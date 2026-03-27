# Reisa Integration Codebase Snapshot

> Scope: planning-only snapshot of the current codebase for integrating Reisa Service API. No runtime code changes applied.

## 1) Repository overview (integration-focused tree)

```text
backend/
  app.py                        # process bootstrap, threads, scanner, cleanup
  flask_server.py               # Flask app, auth wrappers, admin + generate_code routes, blueprint mount
  metrics.py                    # in-memory counters/gauges/histograms
  controllers/
    machine_control.py          # core scan validation, UI state, start orchestration, usage decrement
    telemetry.py                # machine state store + polling + runstate transitions
    qr_scanner.py               # serial scanner listener -> handle_scanned_code
    ui_api.py                   # /api routes used by frontend + kiosk
    code_generator.py           # create code + usage_limit + expiration
    code_cleanup.py             # remove expired codes + logs
  models/
    __init__.py                 # sqlite engine/session/base/init_db
    code_model.py               # codes table
    scan_log_model.py           # scan_logs table
    setting_model.py            # settings table + helper accessors
    device_model.py             # devices table (Shelly/i4/UNI)
    machine_model.py            # machines + machine_configs tables
  setup/
    seed_settings.py            # default settings + api key generation
    seed_machines.py            # default devices + machine configs
    setup_logs.py               # legacy log dir bootstrap script
  utils/
    logger.py                   # root/event/error logging with filters + .env loading
    shelly_control.py           # Shelly gen1/gen2 control + retry
  scripts/
    get_api_key.py              # read api_key from settings
frontend/
  src/App.jsx                   # polls ui_state and screen routing
  src/api/backend.js            # frontend API helper, X-API-KEY injection
README.md                       # architecture and operational notes
run-backend.sh                  # backend launcher
requirements.txt                # runtime dependencies (Flask, SQLAlchemy, requests, serial, etc.)
```

## 2) Relevant code extraction

Below are high-signal files for Reisa planning with practical excerpts and connection notes.

### `backend/app.py`
**What it does:** top-level process startup, DB/bootstrap side effects, background workers.
**Connections:** imports `flask_server`, scanner, telemetry, cleanup; this is the true lifecycle orchestrator.

```python
configure_logger()
init_db()
bootstrap_settings()
bootstrap_devices_and_machines()
ensure_backend_relay_setting_exists()
...
threading.Thread(target=start_flask, daemon=True).start()
start_telemetry_poll()
threading.Thread(target=cleanup_scheduler, daemon=True).start()
start_scanner_listener()
```

Key side effects:
- DB and settings seeded on import/start.
- Flask server runs in background thread, not as primary process.
- Scanner listener and telemetry loop always start in-process.

---

### `backend/flask_server.py`
**What it does:** creates Flask app; configures CORS from DB; defines auth decorators; exposes admin + code generation routes; mounts `ui_api` blueprint under `/api`.
**Connections:** uses global SQLAlchemy `session`, settings model, code model, scan logs, metrics.

Key setup excerpt:
```python
allowed_origins = get_setting_value(session, "cors_allowed_origins", "")
origins_list = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, origins=origins_list)
app.register_blueprint(ui_api, url_prefix="/api")
```

Auth excerpt:
```python
def require_api_key(view_function):
    ...
    header_key = request.headers.get("X-API-KEY")
    db_key = get_setting_value(session, "api_key")
```

Current external write endpoint:
```python
@app.route("/generate_code", methods=["POST"])
@require_api_key
def generate_code():
    ...
    response = generate_new_code(order_id, usage_limit)
```

Admin routes include metrics, scan logs, code lookup/delete, and settings update.

**Important integration note:** Route responsibilities are mixed (admin, API key auth, settings mutation, code domain logic). No dedicated service layer.

---

### `backend/controllers/ui_api.py`
**What it does:** kiosk-facing API used by frontend and likely button-webhook integrations.
**Connections:** calls machine_control directly; enforces API key via DB settings.

Routes:
```python
@ui_api.route("/scan_code", methods=["POST"])
@ui_api.route("/start_machine", methods=["POST"])
@ui_api.route("/ui_state", methods=["GET"])
@ui_api.route("/i4_event", methods=["POST", "GET"])
```

Flow excerpt:
```python
success, message, code_info = handle_scanned_code(code, source="api")
...
code_info, msg = validate_code(code)
ok, message = start_machine(code_info, machine_id)
```

**Important integration note:** `scan_code` and `start_machine` are split endpoints, but both still depend on local `Code` model validation.

---

### `backend/controllers/qr_scanner.py`
**What it does:** serial port scanner ingestion.
**Connections:** scans call the same `handle_scanned_code` path used by API scans.

Excerpt:
```python
SERIAL_PORT = get_setting_value(session, "serial_port", default="/dev/ttyACM0")
...
success, message, _ = handle_scanned_code(decoded, source="scanner")
```

**Integration relevance:** this is the physical code ingress point. Any Reisa lookup-by-token/PIN must hook here (or in shared handler it calls).

---

### `backend/controllers/machine_control.py` (core)
**What it does:** central business logic for validation, UI state transitions, machine start orchestration, telemetry callbacks, usage decrement, scan logging.

#### Validation + scan acceptance
```python
def validate_code(code: str) -> Tuple[Optional[ValidatedCode], str]:
    obj = db.query(Code).filter_by(code=code).first()
    if not obj: return None, "Code expired or invalid."
    if obj.expiration_date and obj.expiration_date <= datetime.utcnow(): ...
    if obj.current_usage >= obj.usage_limit: ...
```

```python
def handle_scanned_code(raw_code, source):
    ready, message = require_ready_to_scan(source, code)
    code_info, msg = validate_code(code)
    ...
    write_scan_log(code, code_info.order_id, "valid", source)
    arm_code(code_info)
    update_ui_state({"state": "choose_machine", ...})
```

#### Usage decrement (current source of truth)
```python
def _apply_usage_delta(code_info):
    obj = db.query(Code).filter_by(code=code_info.code).first()
    obj.current_usage += 1
    uses_left = max(obj.usage_limit - obj.current_usage, 0)
    if obj.current_usage >= obj.usage_limit:
        obj.expiration_date = datetime.utcnow() + timedelta(days=1)
    db.commit()
```

#### Machine start orchestration
```python
def start_machine(code_info, machine_id):
    runtime = _resolve_machine(machine_id)
    if not runtime or not runtime.available: return False, "Machine not available."
    ...
    _store.mark_pending_start(machine_id)
    if backend_control_enabled:
        success = shelly_switch_on(runtime.uni_device)
        if not success: return False, "Machine start failed."
    timer = threading.Timer(_selection_timeout_seconds(), _selection_timeout, args=[machine_id])
    _pending_starts[machine_id] = PendingStart(...)
```

#### Telemetry-confirmed completion of start
```python
def _on_runstate_started(machine_id: str) -> None:
    pending = _pending_starts.pop(machine_id, None)
    ...
    _handle_successful_start(machine_id, pending.code)
```
`_handle_successful_start` calls `_apply_usage_delta` and updates UI/metrics.

**Integration relevance:** this file is the highest-value Reisa insertion point. It currently couples scan validation, machine start, local usage debit, UI state, and logging.

---

### `backend/controllers/telemetry.py`
**What it does:** in-memory machine state (`MachineStateStore`), polling Shelly metrics, runstate transitions, event dispatch.

Key behavior:
- `RUNSTATE_AVAILABLE`, `RUNSTATE_IN_USE`, `RUNSTATE_OFFLINE`.
- Polls devices based on `metric_source` and per-machine config thresholds.
- Emits events: `runstate_started`, `runstate_stopped`, `device_offline`.

Excerpt:
```python
if value >= threshold_on ...:
    store.transition_to_in_use(ctx.slug)
    store.clear_pending_start(ctx.slug)
elif value <= threshold_off ...:
    if runtime.run_state == RUNSTATE_IN_USE ...:
        store.transition_to_available(ctx.slug)
```

**Integration relevance:** the reliable “machine actually started” signal currently comes from telemetry transition, not Shelly command success alone.

---

### `backend/controllers/code_generator.py` and `code_cleanup.py`
`code_generator.py`: creates local `Code` rows with `usage_limit/current_usage/expiration_date`.
`code_cleanup.py`: daily purge of expired codes and related scan logs.

**Integration relevance:** local code issuance may become legacy/fallback if Reisa is source-of-truth for usage entitlement.

---

### `backend/models/*`
**Current database truth:**
- `codes` (`Code`): token, order_id, usage_limit, current_usage, expiration_date.
- `scan_logs` (`ScanLog`): scan attempts + results.
- `settings` (`Settings`): dynamic runtime config and secrets (`api_key`, admin creds, timeouts).
- `devices`, `machines`, `machine_configs`: machine inventory + telemetry config.

**Critical architectural issue:** `backend/models/__init__.py` defines a global `session = Session()` while other code also creates per-call `Session()`; mixed session lifetimes across threads.

---

### `backend/utils/shelly_control.py`
**What it does:** Shelly relay command abstraction (gen1/gen2 detect, retries, RTT metrics).
**Integration relevance:** used by machine start path; contains retry/error semantics that should be reflected in Reisa status posting behavior.

---

### `backend/utils/logger.py`
**What it does:** configures root/event/error rotating logs, applies request sampling/redaction/filters, loads `.env`.
**Integration relevance:** best place to ensure Reisa request/response audit fields are logged consistently (without leaking secrets).

---

### Setup/bootstrap files
- `backend/setup/seed_settings.py` seeds defaults and auto-generates `api_key`.
- `backend/setup/seed_machines.py` seeds default devices/machines/config.

Integration implication: add Reisa settings either as seeded settings keys or true env vars (or both with precedence).

---

### Frontend communication (`frontend/src/api/backend.js`, `frontend/src/App.jsx`)
- Frontend polls `/api/ui_state` every 1 second.
- Frontend attaches `X-API-KEY` from `VITE_API_KEY` or localStorage.
- UI is driven entirely by backend state machine fields (`waiting_for_code`, `choose_machine`, `machine_starting`, `machine_in_use`, `error`).

Integration implication: minimal frontend changes needed if backend preserves these states/messages.

## 3) Current operational flow (reconstructed)

1. **Process start (`backend/app.py`)**
   - logger configured.
   - DB initialized.
   - settings/machines bootstrapped.
   - backend relay setting ensured.
2. **Flask server thread starts (`start_flask`)** loading `backend/flask_server.app`.
3. **Telemetry poll thread starts** and continuously refreshes machine definitions + polls metrics.
4. **Cleanup scheduler thread starts** and runs `cleanup_expired_codes()` daily.
5. **QR scanner listener starts** (if serial available) and loops forever.

### Scan flow (scanner or API)
6. Scanned value enters via:
   - serial scanner -> `qr_scanner._handle_scanned_value()`
   - API -> `POST /api/scan_code`.
7. Both paths call `machine_control.handle_scanned_code()`.
8. `require_ready_to_scan` rejects scans unless UI state is `waiting_for_code`.
9. `validate_code` checks local `codes` table (existence/expiry/usage limit).
10. Valid scan is logged in `scan_logs`, code is armed for button selection timeout, UI moves to `choose_machine` with machine snapshot.

### Machine start flow
11. Start request enters via:
   - `POST /api/start_machine` (explicit machine_id + code)
   - `POST/GET /api/i4_event` -> button index resolves machine for currently armed code.
12. `start_machine` checks machine availability from telemetry store.
13. Marks pending start; optionally sends Shelly ON command (depending on `backend_relay_enabled`).
14. Sets timeout timer for selection confirmation.
15. Telemetry polling detects runstate transition to `in_use` and emits `runstate_started`.
16. `machine_control._on_runstate_started` consumes pending start and calls `_handle_successful_start`.
17. `_handle_successful_start` decrements local code usage (`_apply_usage_delta`) and updates UI (`machine_in_use` then auto-reset).

### Availability/state tracking
- availability is runtime, in-memory, telemetry-derived (`MachineStateStore.available`).
- DB machine rows define topology/config; live state is not persisted.

### Logging
- request logs in root logger + metrics.
- events/errors in dedicated files.
- scan attempts persisted to `scan_logs` table.

### Settings
- mostly DB-backed (`settings` table).
- env var override currently only explicit for `LOG_LEVEL` and frontend Vite values.

## 4) Integration-relevant findings (where Reisa should hook)

- **Current code validation:** `machine_control.validate_code` (local `codes` query).
- **Scanned code ingress:** `qr_scanner._handle_scanned_value` and `/api/scan_code` route.
- **Usage decrement today:** `machine_control._apply_usage_delta` called only on telemetry-confirmed start.
- **Machine start trigger:** `machine_control.start_machine` (`shelly_switch_on`, pending start, timeout).
- **Session/state recording:** in-memory `UI_STATE`, `_pending_starts`, `_armed_code`, and telemetry store.
- **Errors/retries:** Shelly retries in `utils/shelly_control`; scan/start failures mostly immediate with UI error state.
- **Where to add routes:** `controllers/ui_api.py` (kiosk flow) and/or `flask_server.py` (admin/integration routes).
- **Where integration modules should live:** new `backend/integrations/` package (not currently present).
- **Where env vars/settings should be added:** `seed_settings.py` + runtime settings accessors in `setting_model.py` and `logger` pattern.
- **Where audit logs should be added:** event logger + DB audit table (new model) at orchestration boundaries.

## 5) Technical risks and architecture issues (blunt)

1. **Business logic is controller-heavy and stateful.** `machine_control.py` is doing orchestration, validation, DB writes, UI state, metrics, timeout logic.
2. **Global SQLAlchemy session mixed with ad-hoc sessions** across threads (`session` singleton + `Session()` calls) risks stale state/thread safety issues.
3. **No service layer abstraction.** Replacing local validation with external Reisa currently requires editing controller internals directly.
4. **Hidden in-memory state transitions** (`_armed_code`, `_pending_starts`, timers) are fragile and not persisted.
5. **Start confirmation is asynchronous/indirect** (telemetry event). Any external deduct/status call must be carefully sequenced.
6. **Auth and admin concerns mixed in same module** (`flask_server.py`), including destructive delete routes without `@require_admin_auth` on two DELETE endpoints.
7. **Settings are mostly stringly typed DB values.** Missing schema/type enforcement for integration credentials/timeouts.
8. **Error handling lacks explicit retry policy for external service APIs** (Reisa will need robust idempotent handling).
9. **Startup has heavy side effects** (seeding/init at import/start) that complicate deterministic deployments/tests.
10. **Potential legacy drift**: local code generation/expiry model may conflict conceptually with Reisa usage truth.

## 6) Proposed Reisa integration plan (repo-specific)

### Proposed file layout
- `backend/integrations/reisa_client.py`
- `backend/integrations/reisa_service.py`
- `backend/integrations/__init__.py`
- optional: `backend/models/reisa_audit_model.py`
- optional: `backend/services/start_orchestrator.py` (extract from controller)

### Responsibilities
- **`reisa_client.py`**: raw HTTP client (`GET /info`, lookup by uuid/pin, deduct, metadata, status), auth header, timeouts, retries, response normalization.
- **`reisa_service.py`**: domain orchestration helpers:
  - `lookup_service(token_or_pin)`
  - `remaining_uses(service) = totalQuantity - usedQuantity`
  - `mark_start(uuid)`, `deduct(uuid, qty=1)`, `mark_complete(uuid)`, `merge_metadata(uuid, data)`
  - map Reisa errors to app-friendly messages/status.
- **Controller layer (`ui_api.py` / `machine_control.py`)** should call service methods, not directly call external HTTP.

### What stays mostly untouched
- telemetry polling and machine availability logic (`telemetry.py`).
- Shelly command utilities (`shelly_control.py`).
- frontend polling contract (`/api/ui_state` states).

### What should be refactored/extended
- `machine_control.validate_code` -> become adapter that can use Reisa lookup (primary) and local code model (fallback/legacy mode).
- `_apply_usage_delta` -> become strategy:
  - Reisa-primary: call Reisa deduct after confirmed start.
  - local fallback: existing DB increment.
- add explicit transaction-like orchestration around start-confirm-deduct-status with robust failure logging.

### Legacy/local code model decision
- **Recommendation:** keep `Code` model as **legacy/fallback + optional offline mode**, not source-of-truth for usage when Reisa is enabled.
- keep scan_logs + new audit table as local operational and compliance truth.

## 7) Reisa Service API Summary

Planning assumptions for implementation:

Authentication:
- Bearer token auth is required.

Endpoints:
- GET /info
  Purpose: get service type and site information based on bearer token
  Example response fields:
    - siteName
    - siteNameEnglish
    - siteSlug
    - serviceName
    - serviceType
    - timestamp

- GET /uuid/{uuid}
  Purpose: look up a service by UUID/token
  Example response fields:
    - transactionNumber
    - bookingNumber
    - serviceId
    - token
    - pinCode
    - customer.name
    - customer.email
    - details.totalQuantity
    - details.usedQuantity
    - metadata.lastUsed

- GET /pin/{pin}
  Purpose: look up a service by PIN code
  Response shape is similar to UUID lookup

- POST /uuid/{uuid}/deduct
  Purpose: deduct from the service's usedQuantity
  Request body:
    { "quantity": 1 }
  Example response:
    {
      "successful": true,
      "usedQuantity": 3,
      "remainingQuantity": 2
    }
  Important behavior:
    - 400 if quantity is invalid or would exceed total

- POST /uuid/{uuid}/metadata
  Purpose: merge key-value metadata into existing metadata
  Request body example:
    {
      "metadata": {
        "lastUsed": "2024-01-22T14:00:00Z",
        "temperature": "40C"
      }
    }
  Example response:
    {
      "successful": true,
      "metadata": {
        "lastUsed": "2024-01-22T14:00:00Z",
        "temperature": "40C"
      }
    }

- POST /uuid/{uuid}/status
  Purpose: post service status action
  Request body example:
    { "action": "WASHING_MACHINE_START" }
  Known example actions:
    - WASHING_MACHINE_START
    - WASHING_MACHINE_COMPLETE
  Example response:
    { "successful": true }
  Important behavior:
    - 400 if action is invalid

## 8) Recommended operational flow for this repo (target)

### Proposed target flow
1. user scans QR or enters PIN
2. backend looks up service in Reisa
3. backend checks remaining uses using `totalQuantity - usedQuantity`
4. backend verifies machine availability locally
5. backend sends machine start command locally
6. only after confirmed successful machine start:
   - send Reisa status `WASHING_MACHINE_START`
   - deduct quantity 1
7. when machine completes:
   - send `WASHING_MACHINE_COMPLETE`
   - optionally update metadata

### Why deduct must happen after confirmed start
- Current architecture confirms real start via telemetry transition, not just command dispatch.
- Deducting before confirmation risks charging for failed starts (relay/network/machine offline/timeout).
- Post-confirm deduct keeps customer entitlement and machine operation consistent.

### Current vs target gap summary
- Current: local DB validation/decrement.
- Target: Reisa validation/decrement with local machine-state gating and local audit persistence.

## 9) Concrete TODO list

### Phase 1: discovery/read-only integration
- [ ] Add `backend/integrations/reisa_client.py` with `GET /info` and health probe.
- [ ] Add settings/env plumbing: `REISA_BASE_URL`, `REISA_BEARER_TOKEN`, timeout/retry settings.
- [ ] Add structured logging fields for reisa request id/status/endpoint.
- [ ] Add admin diagnostic endpoint to verify Reisa connectivity (read-only).

### Phase 2: lookup flow
- [ ] Implement lookup by UUID and PIN in `reisa_service.py`.
- [ ] Update scan handling path to resolve scanned payload format (uuid/pin/local legacy).
- [ ] Replace `validate_code` with strategy-based validator (reisa primary, local fallback).
- [ ] Return remaining uses from Reisa in UI response payload.

### Phase 3: machine start orchestration
- [ ] Refactor machine start success path into explicit orchestration unit.
- [ ] On telemetry-confirmed start: call Reisa status start then deduct(1).
- [ ] Ensure idempotency guards for duplicate telemetry events/timeouts.
- [ ] Add robust retry/backoff and dead-letter logging for failed Reisa writes.

### Phase 4: completion, metadata, audit logs
- [ ] Hook telemetry `runstate_stopped` -> send `WASHING_MACHINE_COMPLETE`.
- [ ] Add optional metadata posting (e.g., `lastUsed`, machine id, cycle metrics).
- [ ] Create local audit model/table for Reisa calls + outcomes + correlation IDs.
- [ ] Add admin route(s) to inspect Reisa audit trail.

### Phase 5: cleanup/refactor/hardening
- [ ] Split `machine_control.py` into controller + service/orchestrator modules.
- [ ] Normalize session management (remove global session anti-pattern).
- [ ] Enforce auth on all destructive admin endpoints.
- [ ] Add integration tests for: scan->start success, start fail no-deduct, deduce retry, completion flow.
- [ ] Decide and document final legacy behavior of `codes` table in production mode.

## Appendix A: Discovered routes

- `POST /generate_code`
- `GET /admin/metrics`
- `GET /admin/metrics/export.csv`
- `GET /admin/usage/by_order_id/<order_id>`
- `GET /admin/usage/by_code/<code>`
- `GET /admin/scan_logs/last/<int:count>`
- `GET /admin/codes`
- `GET /admin/codes/last/<int:count>`
- `GET /admin/codes/by_order_id/<order_id>`
- `GET /admin/codes/<code>`
- `DELETE /admin/codes/<code>`
- `DELETE /admin/codes/by_order_id/<order_id>`
- `PUT /admin/settings/cors`
- `GET|PUT /admin/settings/<key>`
- `POST /api/scan_code`
- `POST /api/start_machine`
- `GET /api/ui_state`
- `GET|POST /api/i4_event`

## Appendix B: Major env/settings keys discovered

- env vars:
  - `LOG_LEVEL`
  - `VITE_API_BASE_URL`
  - `VITE_API_KEY`
- DB-backed settings keys in active code:
  - `api_key`
  - `admin_username`
  - `admin_password_hash`
  - `cors_allowed_origins`
  - `log_level`
  - `button_select_timeout_sec`
  - `selection_timeout_sec`
  - `backend_relay_enabled`
  - `serial_port`
  - `serial_baudrate`
  - `scan_timeout`
  - `code_expiration_days`

