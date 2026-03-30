# Runtime Lifecycle

## Purpose
This document explains what starts, in what order, and with which side effects when running the system.

It is the canonical reference for startup behavior and should be read before changing entrypoints, background workers, or bootstrap code.

---

## Entrypoints at a glance

### Primary operational entrypoint
- `python -m backend.app`

### Alternate Flask-only entrypoint
- `python -m backend.flask_server`

### Frontend runtime entrypoint
- `cd frontend && npm run dev`

---

## Backend startup sequence (`backend/app.py`)
When `backend.app` is imported/launched:
1. `configure_logger()`
2. `init_db()`
3. `bootstrap_settings()`
4. `bootstrap_devices_and_machines()`
5. `ensure_backend_relay_setting_exists()`
6. Imports controllers/services that depend on initialized DB.

When `__main__` runs:
1. start Flask server in daemon thread (`start_flask`)
2. start telemetry polling (`start_telemetry_poll`)
3. start cleanup scheduler thread (24h loop)
4. start Reisa retry worker thread (`run_retry_worker_loop`, settings-gated)
5. start scanner listener (`start_scanner_listener`)
6. keep main thread alive with sleep loop

Operational implication: `backend.app` is the full runtime orchestrator and should be the default for kiosk-like operation.

---

## What `backend/flask_server.py` does
Import-time behavior includes:
- `configure_logger()`
- `init_db()`
- `bootstrap_devices_and_machines()`
- Flask app creation and CORS init from DB setting
- blueprint registration (`/api` routes)

Request lifecycle behavior:
- assigns request ID in `before_request`
- logs duration/status/route in `after_request`
- updates in-process metrics counters/histograms
- injects `X-Request-ID` into response
- tears down scoped DB session in app context teardown

Routes include:
- code generation (`/generate_code`)
- admin code/usage/settings routes
- Reisa diagnostics/retry/replay/admin routes
- metrics export routes

Operational implication: running `backend.flask_server` directly provides HTTP routes but does **not** launch full worker set the same way `backend.app` does.

---

## Startup mode delta (operator-critical)

## `python -m backend.app`
- runs settings bootstrap (`bootstrap_settings`) including first-run API key generation if missing,
- runs `ensure_backend_relay_setting_exists` (inserts missing key as `false`),
- launches full worker/thread set.

## `python -m backend.flask_server`
- does **not** run `bootstrap_settings`,
- does **not** run `ensure_backend_relay_setting_exists`,
- serves HTTP routes only.

Operational implication:
- on fresh/uninitialized settings, Flask-only startup can leave `api_key` missing (auth not ready for normal operation),
- missing `backend_relay_enabled` key is interpreted via code fallback when machine-start path evaluates relay behavior.

---

## Background worker/thread map

### From `backend.app`
- Flask server thread
- Telemetry poll thread (`backend/controllers/telemetry.py`)
- Cleanup scheduler thread (`backend/controllers/code_cleanup.py` every 24h)
- Reisa retry worker thread (`backend/services/reisa_retry_service.py`, gated by settings)
- Scanner listener thread (`backend/controllers/qr_scanner.py`, only if serial available)

### From telemetry system
- Telemetry loop refreshes machine definitions repeatedly from DB and polls configured device metrics.
- Machine state transitions emit callbacks used by start orchestration (`runstate_started` and `runstate_stopped`).

---

## Bootstrap side effects

### Settings bootstrap
`backend/setup/seed_settings.py`:
- inserts default settings when missing,
- ensures API key exists,
- logs generated key first run.

### Devices/machines bootstrap
`backend/setup/seed_machines.py`:
- seeds default devices/machines only when tables are empty,
- creates machine config rows with threshold defaults.

### Notable ambiguity/risk
`backend.app` and `backend.flask_server` both perform initialization/bootstrap calls. This is currently functional but creates side-effect coupling and should be treated carefully during refactors.

---

## DB/session lifecycle notes
- Engine is SQLite (`sqlite:///codes.db`).
- A scoped session proxy (`session`) exists for many legacy call sites.
- Some services/controllers use explicit short-lived sessions via `Session()`.
- Flask app context teardown calls `remove_session()`.

Operational implications:
- mixed session patterns exist,
- background threads + scoped session usage requires caution,
- avoid introducing long-lived shared transactional state across threads.

---

## Request lifecycle basics
1. Request enters Flask route.
2. API-key/auth decorators enforce credentials (and Basic auth for admin routes).
3. Controller/service logic executes.
4. Structured request logging + metrics in `after_request`.
5. Scoped session removed in teardown.

---

## Frontend/backend runtime relationship
- Frontend polls `/api/ui_state` every second (`frontend/src/App.jsx`, `frontend/src/api/backend.js`).
- Backend owns authoritative UI state machine (`backend/controllers/machine_control.py`):
  - `waiting_for_code`
  - `choose_machine`
  - `machine_starting`
  - `machine_in_use`
  - `error`
- Frontend is intentionally thin and renders based on backend state.

Operational implication: if frontend appears wrong, inspect backend `UI_STATE` and machine-control flow first.

---

## Operational implications and fragile points
1. **Entrypoint choice matters**: Flask-only start may miss full background behavior.
2. **Seed scripts are not migrations**: existing DB rows are not auto-normalized to new defaults.
3. **Hardware dependency sensitivity**: telemetry/scanner/Shelly behavior depends on live device/network state.
4. **State-machine concurrency**: timers/pending starts/armed code windows can create edge-state incidents.
5. **Reisa replay/retry complexity**: recovery paths are durable but operationally nuanced.
6. **Script drift**: helper scripts use differing environment assumptions (virtualenv path, kiosk browser launcher details).

---

## Recommended operator stance
- Use `python -m backend.app` for realistic runtime behavior.
- Treat startup logs as part of health check, not just process up/down.
- Keep a known-good rollback commit and DB backup before upgrades.
- Use troubleshooting matrix and Reisa playbook for incident response.

---

## Related docs
- Install and bootstrap: [`../operations/runbooks/install-and-bootstrap.md`](../operations/runbooks/install-and-bootstrap.md)
- Update/upgrade: [`../operations/runbooks/update-and-upgrade.md`](../operations/runbooks/update-and-upgrade.md)
- Recovery/rollback: [`../operations/runbooks/recovery-and-rollback.md`](../operations/runbooks/recovery-and-rollback.md)
- Troubleshooting matrix: [`../operations/runbooks/troubleshooting-matrix.md`](../operations/runbooks/troubleshooting-matrix.md)
- AI quick map: [`../ai/system-quick-map.md`](../ai/system-quick-map.md)
- Runtime/process ops: [`../operations/runbooks/runtime-and-process-management.md`](../operations/runbooks/runtime-and-process-management.md)
- Auth/admin ops: [`../operations/runbooks/auth-and-admin-access.md`](../operations/runbooks/auth-and-admin-access.md)
