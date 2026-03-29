# System Quick Map

## High-signal repo overview
Vending Washer is a touch-first kiosk system with:
- Flask backend controlling scan/start flows,
- React frontend rendering backend UI state,
- SQLite for codes/settings/machine/integration lifecycle,
- Shelly + scanner hardware integration,
- optional Reisa provider for external entitlement/sync.

---

## Entry points

### Backend
- Full runtime: `python -m backend.app`
- Flask-only: `python -m backend.flask_server`

### Frontend
- Dev runtime: `cd frontend && npm run dev`

### Seed/bootstrap scripts
- `python -m backend.setup.seed_settings`
- `python -m backend.setup.seed_machines`

### Utilities
- API key: `python backend/scripts/get_api_key.py`
- Scanner test: `python tools/test_scanner.py`

---

## Major backend flows

### 1) Scan ingress flow
- API scan route: `backend/controllers/ui_api.py` (`/api/scan_code`)
- Scanner serial ingress: `backend/controllers/qr_scanner.py`
- Shared orchestration: `backend/services/start_orchestrator.py::ingest_scan`

### 2) Start request flow
- API route: `/api/start_machine`
- Button route: `/api/i4_event`
- Machine control + UI state updates: `backend/controllers/machine_control.py`

### 3) Telemetry confirmation flow
- Telemetry polling/thresholds: `backend/controllers/telemetry.py`
- Runstate callbacks trigger start confirmation/completion updates via orchestrator.

### 4) Provider commit flow
- Provider abstraction: `backend/providers/base_provider.py`
- Local provider: `backend/providers/local_provider.py`
- Reisa provider: `backend/providers/reisa_provider.py`
- Selector: `backend/providers/provider_selector.py`

### 5) Reisa failure/recovery flow
- Audit persistence: `backend/services/reisa_audit_service.py`
- Retry queue: `backend/services/reisa_retry_service.py`
- Replay execution/repair: `backend/services/reisa_replay_service.py`
- Diagnostics payloads: `backend/services/reisa_diagnostics_service.py`

---

## Frontend role
Frontend is intentionally thin:
- polls backend `/api/ui_state` every second,
- maps backend state to screen components,
- sends API key from env/localStorage.

Primary files:
- `frontend/src/App.jsx`
- `frontend/src/api/backend.js`
- `frontend/src/components/*`

---

## Database role
SQLite `codes.db` stores:
- QR codes and usage (`codes`)
- scan attempts (`scan_logs`)
- dynamic settings (`settings`)
- hardware inventory (`devices`, `machines`, `machine_configs`)
- lifecycle/session timeline (`usage_sessions`)
- Reisa reliability state (`reisa_audit_logs`, `reisa_retry_jobs`)

Model definitions: `backend/models/*.py`

---

## Hardware role
- Scanner: serial reader (`qr_scanner.py`)
- Shelly relay control: `backend/utils/shelly_control.py`
- Telemetry and machine availability: `backend/controllers/telemetry.py`
- Button box / i4 interactions: `machine_control.py` + telemetry store mappings

---

## Provider/integration role
- Local mode validates/deducts from local `codes` table.
- Reisa mode validates entitlements externally and performs start/completion sync writes.
- Provider mode controlled by settings (`provider_default`, `provider_reisa_enabled`, Reisa credentials).

---

## Most important models/tables
- `codes`: entitlement source in local mode
- `settings`: runtime config/auth/provider controls
- `machines` + `machine_configs` + `devices`: hardware topology and telemetry behavior
- `usage_sessions`: durable scan/start/commit/completion timeline
- `reisa_audit_logs`: external sync trace history
- `reisa_retry_jobs`: deferred replay queue

---

## Most important risky files
- `backend/app.py` (global startup orchestration)
- `backend/flask_server.py` (import side effects + auth/admin surface)
- `backend/controllers/machine_control.py` (state machine/timers/relay actions)
- `backend/controllers/telemetry.py` (availability transitions)
- `backend/services/start_orchestrator.py` (cross-provider flow ownership)
- `backend/services/reisa_replay_service.py` (state repair/idempotency)
- `backend/setup/seed_*` (bootstrap assumptions)

---

## Fast “read these first”
1. `README.md`
2. `docs/operations/runbooks/install-and-bootstrap.md`
3. `docs/architecture/runtime-lifecycle.md`
4. `docs/reference/settings-catalog.md`
5. `docs/operations/runbooks/troubleshooting-matrix.md`
6. Reisa playbook if integration task

---

## If task is X, read Y first

### Install/setup issues
- Docs: install + troubleshooting matrix
- Code: `backend/setup/seed_settings.py`, `backend/setup/seed_machines.py`

### Startup/runtime anomalies
- Docs: runtime lifecycle + recovery/rollback
- Code: `backend/app.py`, `backend/flask_server.py`

### Auth/API key/admin problems
- Docs: troubleshooting matrix + settings catalog
- Code: auth decorators in `backend/flask_server.py`, `backend/controllers/ui_api.py`

### Scanner/hardware/telemetry issues
- Docs: troubleshooting matrix
- Code: `backend/controllers/qr_scanner.py`, `backend/controllers/telemetry.py`, `backend/utils/shelly_control.py`

### Machine-state/start-flow bugs
- Docs: runtime lifecycle + troubleshooting matrix
- Code: `backend/controllers/machine_control.py`, `backend/services/start_orchestrator.py`

### Reisa sync/replay incidents
- Docs: Reisa operator playbook
- Code: `backend/providers/reisa_provider.py`, `backend/services/reisa_*`

### Settings/config change planning
- Docs: settings catalog
- Code: `backend/models/setting_model.py`, readers in relevant modules

### Test failures
- Docs: install/update runbooks (validation sections)
- Code: `backend/tests/*`

---

## Known ambiguity/drift notes
- Startup/bootstrap calls exist in both `backend/app.py` and `backend/flask_server.py`.
- `run-backend.sh` venv path differs from README conventions.
- Some helper scripts under `Testing_Files/` are legacy and should be used cautiously.
