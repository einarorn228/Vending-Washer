# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run the full backend
```bash
source .venv/bin/activate
python -m backend.app
```
This is the only entrypoint that starts all background threads (telemetry poller, scanner listener, Reisa retry worker, code cleanup scheduler). Use this for all realistic runtime work.

`python -m backend.flask_server` starts Flask HTTP routes only — no background workers, no `bootstrap_settings` run. This path leaves `api_key` unset on a fresh database.

### Run the frontend
```bash
cd frontend && npm install && npm run dev
```
Vite dev server on port 3000, proxies `/api` → `http://localhost:5000`.

### Bootstrap a fresh database
```bash
python -m backend.setup.seed_settings   # inserts defaults + generates api_key
python -m backend.setup.seed_machines   # seeds devices/machines/configs (empty tables only)
```
**Seed scripts are not migrations.** They skip tables that already have rows. Existing data is never modified.

### Get the API key
```bash
python backend/scripts/get_api_key.py
```

### Run tests
```bash
python -m pytest backend/tests/                              # full suite
python -m pytest backend/tests/test_machine_control.py       # single file
python -m pytest backend/tests/test_ui_api.py
python -m pytest backend/tests/test_flask_startup_bootstrap.py
```

Tests never touch the real `codes.db`. `backend/tests/_isolation.py` redirects the engine to a
throwaway file via `VENDING_WASHER_DATABASE_URL` (imported from both `conftest.py` for pytest and
`backend/tests/__init__.py` for `python -m unittest`), and `backend/models` refuses to bind to the
project database while under test. Test `setUp` methods delete `settings`/`machines`/`devices` rows,
so that guard is what stands between a test run and the operator's runtime configuration.

Frontend tests are pure-function only, under `node --test`; there is no component test
harness (no jest, vitest, testing-library or jsdom), deliberately.
```bash
cd frontend && node --test src/dev-admin/help/
```

### Compile the Help Hub
```bash
python -m backend.help.cli            # rewrite both manifests
python -m backend.help.cli --check    # verify the committed manifests are current (exit 1 if stale)
```
Run this after editing anything under `docs/admin-guides/` or `docs/public-help/`, and
commit the regenerated `backend/help/generated/admin-help-manifest.json` and
`frontend/src/generated/public-help-manifest.json` with the content change. Authoring
rules: `docs/admin-guides/README.md`.

## Architecture

### Backend state machine
The backend owns the kiosk UI state. The frontend is a thin polling renderer — it never computes state, it only displays what the backend reports.

The authoritative state dict lives in `backend/controllers/machine_control.py:UI_STATE`. States:
- `waiting_for_code` → idle, ready for scan
- `choose_machine` → code armed, machine selection active
- `machine_starting` → relay pulsed, waiting for telemetry confirmation
- `machine_in_use` → run confirmed, short notice then reset
- `error` → brief error display, auto-resets

All scan and start flows are routed through `backend/services/start_orchestrator.py` (`ingest_scan`, `start_from_touch`, `start_from_button`, `start_from_code`). Do not call machine_control primitives directly from routes.

### Frontend polling contract
`frontend/src/kiosk/hooks/useUiStatePolling.js` calls `GET /api/ui_state` via `frontend/src/api/backend.js:pollState()` — not `App.jsx`, which only picks the route (kiosk, `/dev/admin`, `/dev/kiosk-preview`, `/help`). The cadence is backend-owned: the default is 1000 ms, each response's `poll_interval_ms` (from the `kiosk_poll_interval_ms` setting) re-arms the interval, and values outside 250-10000 ms are rejected in favour of the default. All API calls attach `X-API-KEY` from `VITE_API_KEY` env or `localStorage.API_KEY`. The kiosk UI is structured as:
- `KioskRouter.jsx` — maps `uiState.state` to screen components
- `kiosk/screens/` — one component per state
- `kiosk/dev/KioskPreviewPage.jsx` — hardware-free UI preview at `/dev/kiosk-preview`

### Auth layers
Three distinct auth mechanisms coexist:
1. `/api/*` routes — `X-API-KEY` header (value from `settings.api_key`)
2. `/admin/*` routes — HTTP Basic auth (credentials from `settings.admin_username` / `settings.admin_password_hash`)
3. `/api/dev_admin/*` routes — HTTP Basic auth (same admin credentials) + `dev_admin_enabled=true` kill switch

### Blueprint registration
`backend/flask_server.py` registers two blueprints:
- `ui_api` → `/api`
- `dev_admin_api` → `/api/dev_admin`

Admin/Reisa/code-management routes are defined inline in `flask_server.py`.

### Provider abstraction
`backend/providers/provider_selector.py` resolves which provider handles validation and commit:
- **Local** (`local_provider.py`) — validates against the `codes` table, decrements usage
- **Reisa** (`reisa_provider.py`) — validates entitlements externally, syncs start/completion

Provider is selected per-scan via DB settings (`provider_default`, `provider_reisa_enabled`, Reisa credentials). The local provider is always available as fallback.

### Hardware integration
- **QR scanner** — USB serial, consumed by `backend/controllers/qr_scanner.py`. Serial config is read once, when the port is first opened at startup (`_ensure_serial_ready()`), and cached for the process lifetime; settings changes require a restart.
- **Shelly relays** — `backend/utils/shelly_control.py`. Only fires if `backend_relay_enabled=true` in settings. When false, relay commands are skipped (bench/dry-run mode).
- **Telemetry** — `backend/controllers/telemetry.py` polls UNI device metrics on per-machine intervals, applies thresholds/debounce, and emits `runstate_started`/`runstate_stopped` callbacks that drive start confirmation and completion in `machine_control.py`.

### Database
SQLite file: `codes.db` in the repository root. Key tables: `codes`, `devices`, `machines`, `machine_configs`, `scan_logs`, `settings`, `usage_sessions`, `reisa_audit_logs`, `reisa_retry_jobs`. Models in `backend/models/`.

Mixed session patterns exist: a scoped `session` proxy for legacy call sites, and explicit short-lived `Session()` instances in services/controllers. Avoid long-lived shared transactional state across threads.

### Dev admin panel
Route: `/dev/admin` (frontend) → API at `/api/dev_admin/*`.  
Must set `dev_admin_enabled=true` in settings to unlock. Provides settings editing, machine card layout management, and a Remote Control panel (kiosk state polling, scan injection, machine selection, reset).

### Kiosk preview
Route: `/dev/kiosk-preview?scenario=<name>` renders any kiosk screen without backend polling, hardware, or real scans. Scenarios defined in `frontend/src/kiosk/dev/kioskPreviewScenarios.js`. Use this for all frontend UI work.

## Risky operations

- **Deleting `codes.db`** resets all codes, settings, devices, and machine configs. Rerun seed scripts and update browser API key after.
- **`backend_relay_enabled=true`** sends real Shelly relay commands to hardware. Verify physical mapping before enabling.
- **Auth credential changes** (API key, admin password/username) can lock out the system. Change and verify one credential path at a time.
- **Bulk Reisa retry/replay** (`POST /admin/reisa/retry_due`) should only run after inspecting diagnostics and confirming idempotency. See `docs/integrations/reisa/runbooks/reisa-operator-playbook.md`.

## Key doc references
- `docs/ai/system-quick-map.md` — fast file routing by task type
- `docs/architecture/ui-state-contract.md` — full UI state transition map and failure modes
- `docs/architecture/runtime-lifecycle.md` — startup sequence, thread map, bootstrap side effects
- `docs/reference/settings-catalog.md` — all configurable settings with defaults and risk levels
- `docs/operations/runbooks/troubleshooting-matrix.md` — symptom → cause → fix index
- `docs/admin-guides/README.md` — how the Help Hub corpus is authored and compiled
- `docs/CURRENT_STATE.md` — verified snapshot of what actually runs, and what is not implemented
- `AGENTS.md` — repository-wide operating rules for AI agents
