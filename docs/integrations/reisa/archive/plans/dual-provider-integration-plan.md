# Reisa Dual-Provider Integration Plan

## 1. Executive Summary
The current system is a **local-first washer vending stack**: QR codes are generated and validated locally, machine availability is inferred locally via telemetry polling, machine start commands are issued locally via Shelly control, and usage counters are debited in the local SQLite DB only after telemetry confirms the run started.

The target product should become a **dual-provider platform**:
- **Local mode** keeps the existing local QR/usage model and minimal external dependencies.
- **Reisa mode** delegates entitlement/booking authority to Reisa APIs while still keeping local machine control, local UI state, and local persistence for operational truth.

A dual-provider architecture is correct because:
1. It preserves today’s proven local flow for resilience and fallback.
2. It prevents vendor lock-in by making entitlement source pluggable.
3. It allows phased rollout (site-by-site/provider-by-provider) without rewriting core hardware orchestration.

Reisa should be treated as an **external entitlement/usage provider**, not the core app, because this repo already owns critical edge responsibilities (scanner ingress, telemetry runstate confirmation, relay control, kiosk UX, and local audit). Replacing those with provider-specific logic would increase operational risk and reduce flexibility.

## 2. Current System Architecture
This section reflects the actual repository behavior.

### Startup / process lifecycle
- `backend/app.py` performs startup side effects: logging config, DB init, settings bootstrap, machine/device bootstrap, and backend relay setting guard; then starts Flask, telemetry polling, cleanup scheduler, and scanner listener threads.
- `backend/flask_server.py` also calls logger + DB + seed bootstrap at import time, so initialization side effects currently exist in both entry and server modules.

### Flask routes and API boundaries
- `backend/flask_server.py` hosts top-level routes (`/generate_code`, admin metrics/usage/codes/settings endpoints).
- `backend/controllers/ui_api.py` is mounted as `/api` and handles kiosk routes (`/scan_code`, `/start_machine`, `/ui_state`, `/i4_event`).
- API key auth is enforced in `ui_api.before_request` and again separately for `/generate_code` in `flask_server.py`.
- Admin auth uses basic auth wrappers, but delete endpoints for `/admin/codes/...` currently do not carry `@require_admin_auth` (security concern and architectural inconsistency).

### QR scanning flow
- `backend/controllers/qr_scanner.py` opens serial scanner settings from DB (`serial_port`, `serial_baudrate`, `scan_timeout`) and sends valid decoded strings into `machine_control.handle_scanned_code(..., source="scanner")`.
- API scans (`/api/scan_code`) use the same shared handler, giving one business path for scanner/API ingress.

### Machine control flow
- Core orchestration is concentrated in `backend/controllers/machine_control.py`.
- `start_machine` checks machine config/availability from `MachineStateStore`, marks pending start, optionally sends local relay command (`shelly_switch_on`) if backend relay is enabled, and starts a timeout timer.
- Actual successful start is finalized only when telemetry emits `runstate_started` and `machine_control._on_runstate_started` processes pending start.

### Local code validation / usage handling
- Validation is local DB only (`validate_code` queries `Code`, checks expiration and usage limits).
- Usage decrement currently happens in `_apply_usage_delta` inside the telemetry-confirmed success flow, not at scan time and not at relay-command-send time.

### Database models
- `backend/models/code_model.py`: local entitlement (`codes`).
- `backend/models/scan_log_model.py`: scan attempts and outcomes (`scan_logs`).
- `backend/models/setting_model.py`: string key/value settings (`settings`).
- `backend/models/device_model.py` + `backend/models/machine_model.py`: hardware/device inventory, UI machine mapping, telemetry thresholds.
- DB engine uses SQLite (`sqlite:///codes.db`) in `backend/models/__init__.py`.

### Telemetry / runstate events
- `backend/controllers/telemetry.py` maintains in-memory machine runtime state (`MachineStateStore`) and polls Shelly metrics.
- It emits `runstate_started`, `runstate_stopped`, `device_offline` events that downstream listeners (machine control) consume.
- Machine availability in UI is primarily derived from this in-memory telemetry store.

### UI state handling
- `machine_control.UI_STATE` is a global in-memory dict with locking and timers (`waiting_for_code`, `choose_machine`, `machine_starting`, `machine_in_use`, `error`).
- Frontend (`frontend/src/App.jsx`) polls `/api/ui_state` every second and renders screens based on state.

### Settings/config handling
- Settings are persisted in DB as strings with helpers (`get_setting_value`, `update_setting_value`).
- Bootstrapped defaults include API key, log level, button timeout, and admin credentials.
- Runtime code frequently parses strings to int/float/bool ad hoc (e.g., timeout values, relay toggles).

### Logging
- `backend/utils/logger.py` configures root logs + dedicated event/error rotating files and sampling/redaction filters.
- Request logging and metrics are applied via Flask `before_request`/`after_request` in `flask_server.py`.

## 3. Current End-to-End Flow Reconstruction
### Reconstructed happy path (current local flow)
1. System starts (`backend/app.py`), telemetry and scanner background loops begin.
2. A scan enters either via serial (`qr_scanner`) or API (`/api/scan_code`).
3. `handle_scanned_code` rejects if UI is not `waiting_for_code` (busy gate).
4. `validate_code` checks local `codes` table (exists, not expired, usage remaining).
5. Scan is logged into `scan_logs`, code is “armed” for i4 button path, UI moves to `choose_machine`, machine snapshot comes from telemetry store.
6. Machine choice arrives either via `/api/start_machine` with explicit machine ID or `/api/i4_event` button index -> mapped machine.
7. `start_machine` validates availability from local runtime store, marks pending start, optionally sends local Shelly relay command, and moves UI to `machine_starting`.
8. Telemetry detects on-threshold sustained crossing and emits `runstate_started`.
9. `_on_runstate_started` finalizes start: usage decremented in local `codes`, metrics updated, UI moves to `machine_in_use`, then auto-resets.
10. Later telemetry `runstate_stopped` marks machine available again; no external provider callback exists today.

### Current decrement moment
- Usage decrement happens **after telemetry confirms machine started** in `_handle_successful_start -> _apply_usage_delta`.

### Completion/run-state feedback
- Completion is inferred from telemetry off-threshold transitions (`transition_to_available`) and machine availability is updated in-memory.
- No provider-facing completion API exists in current implementation.

### UI update path
- Backend mutates in-memory `UI_STATE`; frontend polls `/api/ui_state` every second to render.

### What is persisted
- `codes` usage and expiration changes.
- `scan_logs` for accepted/rejected scans.
- Settings, devices, machines, configs in SQLite.
- Telemetry runtime state and pending-start timers are in-memory only.

### Ambiguities / competing or legacy paths
- There are two startup bootstrap sites (`app.py` and `flask_server.py`) creating side-effect duplication risk.
- DB session usage is mixed (global `session` plus per-call `Session()`), increasing transactional ambiguity in multi-thread contexts.
- `/api/start_machine` re-validates code independently, while i4 path uses armed-code state; behavior is split between explicit and implicit machine selection modes.
- Admin delete routes appear unauthenticated relative to other admin routes.

## 4. Product Direction and Final Target State
Target product vision:
- **Local provider mode**: existing QR/code usage authority remains local.
- **Reisa provider mode**: entitlement lookup + usage accounting authority comes from Reisa API.
- **Future optional per-product/per-service provider routing**: provider selection can vary by service SKU/machine group/site policy.

In all modes:
- Local DB remains mandatory for audit/session history/operations.
- Machine control and telemetry confirmation remain local.
- UI state management remains local.
- Provider only swaps entitlement source + usage reporting behavior.

Why this is smarter than Reisa-specific rewrite:
- Commercially: preserves ability to run with or without Reisa, supports multi-tenant provider strategy.
- Technically: isolates unstable external API concerns from deterministic local safety-critical control loop.

## 5. Reisa API Planning Summary
### Reisa API Planning Summary
Planning assumptions for Reisa integration:

#### Authentication
- Bearer token authentication required on all Reisa calls.

#### Endpoints
- `GET /info`
  - Purpose: fetch site/service metadata tied to bearer token.

- `GET /uuid/{uuid}`
  - Purpose: look up service usage entitlement by UUID.
  - Expected payload fields include: `transactionNumber`, `bookingNumber`, `serviceId`, `token`, `pinCode`, `customer.name`, `customer.email`, `details.totalQuantity`, `details.usedQuantity`, `metadata.lastUsed`.

- `GET /pin/{pin}`
  - Purpose: look up service usage entitlement by PIN.
  - Response shape assumed similar to UUID lookup.

- `POST /uuid/{uuid}/deduct`
  - Purpose: deduct usage quantity.
  - Request body example: `{ "quantity": 1 }`.
  - Behavior assumptions: may return `usedQuantity` and `remainingQuantity`; must fail when quantity invalid or exceeds total.

- `POST /uuid/{uuid}/metadata`
  - Purpose: merge metadata associated with entitlement/session.

- `POST /uuid/{uuid}/status`
  - Purpose: post service action/status transitions.
  - Known actions include `WASHING_MACHINE_START` and `WASHING_MACHINE_COMPLETE`.

#### Critical operational rule
- **Do not deduct usage before machine start confirmation**. Deduct/commit must occur only after local telemetry confirms actual machine start.

## 6. Recommended Target Architecture
Recommended structure for this repo:

```text
backend/
  integrations/
    reisa_client.py
    reisa_service.py
  providers/
    base_provider.py
    local_provider.py
    reisa_provider.py
  services/
    start_orchestrator.py
    usage_service.py
  models/
    usage_session_model.py
    reisa_audit_model.py
```

Purpose per file:
- `integrations/reisa_client.py`: low-level HTTP client (auth header, retries/timeouts, endpoint calls, response normalization).
- `integrations/reisa_service.py`: higher-level Reisa operations (lookup by uuid/pin, deduct, status/metadata posting), mapping API semantics to domain outcomes.
- `providers/base_provider.py`: interface/contract used by orchestration regardless of provider.
- `providers/local_provider.py`: wraps current `Code` model behavior (lookup/authorize/commit) behind provider contract.
- `providers/reisa_provider.py`: wraps Reisa entitlement behavior behind same contract and writes local shadow/session records.
- `services/start_orchestrator.py`: central state machine for scan->reserve->start->confirm->commit flow.
- `services/usage_service.py`: local persistence logic for usage sessions and idempotency checks.
- `models/usage_session_model.py`: canonical local session timeline records.
- `models/reisa_audit_model.py`: external call audit and retry/error tracking.

Why this is cleaner:
- Provider abstraction prevents Reisa conditionals from spreading through controllers.
- Start orchestration leaves controllers thin (I/O translation only), reducing duplicated start logic across scan/button/API paths.
- Existing files that should remain thin: `ui_api.py`, `qr_scanner.py`, `flask_server.py` route functions.
- Existing files likely needing extraction: `machine_control.py` (validation/usage commit/provider-specific concerns) and portions of telemetry listener coupling.

## 7. Provider Abstraction Design
Define a common provider contract (business semantics):

1. `lookup(identifier: str, mode: str) -> ProviderLookupResult`
   - Meaning: resolve scan/manual input into entitlement context.
   - `mode` can encode lookup channel (`uuid`, `pin`, `local_code`, or auto).
   - Called immediately after scan ingestion and normalization.

2. `authorize(lookup_result, machine_id: str, now) -> AuthorizationResult`
   - Meaning: confirm entitlement is currently usable (remaining quantity, validity window, policy checks).
   - Called before local machine reservation/start.
   - Must be side-effect free (no deduct yet).

3. `commit_start(session_ref, quantity: int = 1) -> CommitResult`
   - Meaning: finalize one usage after local start confirmation.
   - Local provider: increment/debit local code usage.
   - Reisa provider: post status start (if required) and deduct quantity, return remaining usage.
   - Must be idempotent using local session key.

4. `mark_completion(session_ref, completion_payload) -> CompletionResult`
   - Meaning: notify provider that machine run completed.
   - Local provider may no-op while still recording local completion.
   - Reisa provider sends completion status and optional metadata.

5. `update_metadata(session_ref, metadata: dict) -> MetadataResult` (optional)
   - Meaning: best-effort metadata sync (e.g., machine id, timestamps, trace IDs).
   - Can be async/retry if non-critical.

Provider outputs should include:
- canonical provider reference (`provider`, `external_id`, `booking_number` etc.)
- `remaining_quantity` where available
- `retryable` vs `terminal` error classification

## 8. Orchestrator Flow Design
Ideal final flow:
1. Input arrives from QR scanner or manual/API entry.
2. Active provider resolves identifier (`lookup`).
3. Entitlement is validated/authorized (`authorize`).
4. Machine availability is checked locally (`MachineStateStore`).
5. Machine is reserved locally (pending start marker + local session row).
6. Local start command is sent (if backend relay enabled) or local start-wait state is entered.
7. Actual start confirmation is awaited from telemetry runstate.
8. **Only after confirmed start**:
   - provider `commit_start` occurs,
   - in Reisa mode this includes status + deduct.
9. Local session state is updated (`started_confirmed`, remaining usage snapshot, provider commit status).
10. On later run completion (telemetry stop), invoke provider `mark_completion` (best effort with retry/audit), then close local session.

Why commit point is critical:
- The current code already confirms starts asynchronously via telemetry events. External deduct before confirmation would create charge-without-service failures during relay/network/hardware faults.

## 9. Concrete Repo Touchpoints
Likely touchpoints mapped to current files:

1. `backend/controllers/ui_api.py`
- Stays: route surface (`/scan_code`, `/start_machine`, `/ui_state`, `/i4_event`) and auth guard.
- Extract: direct `validate_code`/`start_machine` coupling.
- Wrap: call orchestrator service with provider-agnostic request DTO.
- Avoid: importing Reisa client/provider directly in route handlers.

2. `backend/controllers/qr_scanner.py`
- Stays: serial reading and decode validity checks.
- Extract: business decision-making.
- Wrap: forward scanner events to orchestrator entrypoint.
- Avoid: provider logic in scanner loop.

3. `backend/controllers/machine_control.py`
- Stays initially: local relay actions, UI state mutations, telemetry listener hookups.
- Extract: code validation + usage debit into providers/services.
- Wrap: pending-start and runstate callbacks through orchestrator session IDs.
- Avoid: hardcoded local code assumptions in finalized architecture.

4. `backend/controllers/telemetry.py`
- Stays: machine state polling and event emission.
- Extract: none required initially.
- Wrap: add orchestrator listener hook for runstate transitions.
- Avoid: any direct Reisa API calls from telemetry thread.

5. `backend/flask_server.py`
- Stays: app creation, request metrics, admin routes.
- Extract: business-heavy route logic over time.
- Wrap: provider settings management and validation endpoint(s).
- Avoid: direct provider commit/deduct calls from HTTP route layer.

6. Settings/config access (`backend/models/setting_model.py`, `backend/setup/seed_settings.py`)
- Stays: persistence mechanism for now.
- Extract: typed config reader/writer module (provider settings schema).
- Avoid: ad hoc string parsing spread across code.

7. Local usage/code models (`backend/models/code_model.py`, `scan_log_model.py`)
- Stays: local provider and compatibility.
- Extract: long-term split into provider-neutral session model.
- Avoid: forcing Reisa state into `codes` table semantics.

8. Logging and audit (`backend/utils/logger.py` + event/error logs)
- Stays: central logging infra.
- Wrap: standardized `provider_event` structured logging, correlation IDs.
- Avoid: logging bearer tokens/raw PII.

## 10. Data Model Plan
Additions for dual-provider operation:

### `usage_sessions` (new)
Purpose: canonical local operational record across providers.
Suggested fields:
- `id` (PK)
- `session_uid` (unique idempotency/correlation key)
- `provider` (`local`, `reisa`, future values)
- `provider_reference` (uuid/booking/token reference)
- `identifier_type` (`code`, `uuid`, `pin`)
- `identifier_value_masked`
- `machine_id`
- `scan_source` (`scanner`, `api`, `manual`)
- `state` (`lookup_ok`, `authorized`, `reserved`, `start_sent`, `start_confirmed`, `commit_ok`, `complete_reported`, `failed`, etc.)
- `requested_quantity`, `committed_quantity`
- `remaining_after_commit` (nullable)
- `error_code`, `error_detail`
- `created_at`, `updated_at`, `started_at`, `completed_at`

### `reisa_audit_logs` (new)
Purpose: durable log of external provider interactions and retries.
Suggested fields:
- `id` (PK)
- `session_uid` (FK-ish reference to usage_sessions)
- `endpoint`, `method`
- `request_payload_redacted`
- `response_status_code`
- `response_payload_redacted`
- `result` (`success`, `retryable_error`, `terminal_error`)
- `attempt_number`
- `latency_ms`
- `created_at`

Current models disposition:
- `codes`: remains **primary** for LocalProvider.
- `scan_logs`: remains **primary** for scan attempt audit; can coexist with usage_sessions.
- `settings`: remains **primary** for runtime config until typed config layer introduced.
- device/machine tables: remain **primary** and provider-agnostic.

## 11. Settings and Configuration Plan
Recommended provider-related settings keys:
- `provider_default` (`local` | `reisa`)
- `provider_local_enabled` (bool string)
- `provider_reisa_enabled` (bool string)
- `reisa_base_url`
- `reisa_bearer_token`
- `reisa_timeout_ms`
- `reisa_connect_timeout_ms`
- `reisa_read_timeout_ms`
- `reisa_completion_reporting_enabled`
- `reisa_metadata_reporting_enabled`
- `reisa_retry_max_attempts`
- `reisa_retry_backoff_ms`

Weaknesses in current settings approach:
- Stringly typed values with scattered parse logic.
- Minimal validation/constraints for required combinations (e.g., Reisa enabled but no token).
- No secret-specific handling/rotation semantics.

Recommendation:
- Introduce a typed config accessor module that validates settings at startup and on admin update.
- Keep DB storage format for backward compatibility, but centralize parse/validation.

## 12. Error Handling and Recovery Plan
Operational truth should remain local (`usage_sessions` + machine state store), with external sync retried from audit queue.

Failure case plan:
1. **Lookup failure**: reject start; UI error; store session with terminal lookup error.
2. **No remaining usage**: reject start; explicit user message; log provider response snapshot.
3. **Machine unavailable**: no provider commit; maintain authorization result only; allow user reselection.
4. **Local start command failure**: no provider commit/deduct; mark local failure; retry allowed.
5. **Machine start never confirmed**: expire pending session by timeout; no deduct; optional provider status `START_FAILED` only if API supports it.
6. **Reisa status failure (start/complete)**: do not block local operation once machine already started/completed; persist retryable audit item.
7. **Reisa deduct failure after confirmed start**: mark `commit_pending_external`; schedule retry; expose manual review dashboard.
8. **Completion reporting failure**: keep session locally completed; retry asynchronously.
9. **Duplicate callbacks / duplicate start attempts**: enforce idempotency by `session_uid` + machine pending state; `commit_start` must tolerate duplicates.
10. **Manual review paths**: admin endpoints or scripts to inspect pending external-sync sessions and replay safely.

## 13. Migration Strategy
### Phase 1: Extract orchestration shape without behavior change
- Goal: create `start_orchestrator` wrapper around existing machine_control flow, preserving local behavior.
- Likely files: `machine_control.py`, new `services/start_orchestrator.py`, `ui_api.py`, `qr_scanner.py`.
- Testing focus: regression on scan gating, start timing, usage decrement point.
- Remaining risk: still coupled to local code model internally.

### Phase 2: Put local mode behind provider abstraction
- Goal: implement `BaseProvider` + `LocalProvider` and route existing validate/debit through provider interface.
- Likely files: new `providers/*`, edits in `machine_control.py` / orchestrator.
- Testing focus: parity for local codes, no behavior drift.
- Remaining risk: dual session handling (global vs scoped) still unresolved.

### Phase 3: Add Reisa read-only lookup
- Goal: integrate Reisa lookup endpoints for validation path without deduct/commit.
- Likely files: `integrations/reisa_client.py`, `reisa_service.py`, `reisa_provider.py`, settings bootstrap.
- Testing focus: lookup success/failure mapping, timeout behavior, masked logging.
- Remaining risk: external API variance in payloads.

### Phase 4: Add Reisa commit after confirmed machine start
- Goal: trigger status + deduct only from telemetry-confirmed start callback.
- Likely files: orchestrator, telemetry listener integration, provider commit path, audit model.
- Testing focus: exactly-once semantics, idempotent retries, no pre-confirm deduct.
- Remaining risk: race conditions in pending-start maps and async callbacks.

### Phase 5: Add completion/metadata/audit logging
- Goal: provider completion and metadata updates with retry queues and observability.
- Likely files: audit model/service, telemetry stop listener, admin diagnostics routes.
- Testing focus: delayed retries, degraded-network operation.
- Remaining risk: backlog growth and operational tooling gaps.

### Phase 6: Cleanup and hardening
- Goal: remove duplicated/legacy paths, secure admin gaps, improve transaction/session safety.
- Likely files: `flask_server.py`, `models/__init__.py`, auth decorators, settings validator.
- Testing focus: concurrency stress, failover drills, security checks.
- Remaining risk: migration complexity if old endpoints remain active.

## 14. Top Architectural Risks
1. **Controller over-concentration**: `machine_control.py` holds scan validation, entitlement, machine commands, UI state, timers, metrics, and DB writes.
2. **Critical in-memory state**: `_pending_starts`, `_armed_code`, `UI_STATE` are process-memory singletons; restart or race can desync sessions.
3. **Mixed SQLAlchemy session patterns**: global `session` and per-call `Session()` across threads can create stale data and transaction ambiguity.
4. **Asynchronous confirmation coupling**: commit timing depends on telemetry callbacks; poorly isolated logic can cause double-commit or missed commit.
5. **Split start paths**: `/start_machine` and i4 button path have slightly different preconditions (explicit code validate vs armed state), increasing divergence risk.
6. **Stringly typed config**: parsing scattered across code with weak validation; misconfig can silently degrade behavior.
7. **Startup side effects duplication**: both `app.py` and `flask_server.py` execute bootstrap init operations.
8. **Security inconsistency in admin endpoints**: delete code routes are not wrapped with admin auth decorators.
9. **Telemetry as single in-process truth**: no persistent machine-state event log for forensic replay.
10. **Legacy/local assumptions in core flow**: current model assumes `Code` is always entitlement source.

## 15. Recommended Next Implementation Steps
Top 10 actions:
1. Define provider domain contracts (`BaseProvider` dataclasses/results/errors).
2. Introduce `start_orchestrator.py` and route both scanner and API/i4 start pathways through it.
3. Implement `LocalProvider` by wrapping existing validate/debit behavior with no behavior change.
4. Add `usage_sessions` model and write session lifecycle states from orchestrator.
5. Add typed provider settings accessor and validation module.
6. Implement `reisa_client.py` with auth, timeout, retries, and redacted logging.
7. Implement `ReisaProvider.lookup/authorize` first (read-only stage).
8. Integrate telemetry-confirmed callback to trigger provider `commit_start` idempotently.
9. Add `reisa_audit_logs` and retry worker/tooling for failed external syncs.
10. Harden security + consistency (admin auth gaps, session lifecycle, startup bootstrap duplication).

What should be coded first:
- Orchestrator shell + LocalProvider abstraction + usage_sessions persistence (no external calls yet).

What should **not** be coded first:
- Direct Reisa deduct inside `/api/start_machine` or scan handlers.
- Reisa-specific conditionals spread through controllers.
- Completion callbacks before start commit idempotency is solved.

Before any production-like rollout verify:
- Deduct happens only post-confirmed start.
- Duplicate events do not double-deduct.
- Offline/timeout scenarios preserve local truth and recover via retry.
- Local mode regression suite passes unchanged behavior.
- Provider switching by config is deterministic and observable.
