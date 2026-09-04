# Vending Washer

Touch-first washer vending prototype consisting of a Flask backend, a React touchscreen UI, and hardware integrations for QR scanners, Shelly relays, and telemetry-backed machine availability.

## Kiosk input architecture (current)
- Touchscreen selection is the primary/default machine selection method in `choose_machine`.
- Physical button-box input is optional and controlled by setting `button_box_enabled`.
- `kiosk_input_mode`/`input_mode` remains legacy compatibility metadata and must not be used to disable touch selection.
- Both touch and button-box selection paths use the same backend start validation flow.

## Beta dev/admin panel
- Route: `/dev/admin`
- Purpose: temporary trusted-local beta panel for whitelisted settings and machine-card layout edits.
- Backend kill switch: `dev_admin_enabled` must be `true`; default is `false`.
- Temporary lock: HTTP Basic auth against `admin_username` / `admin_password_hash` (the same credentials as `/admin/*`), not the kiosk API key; this is not production-grade security.
- Secrets are read-only/masked in the first beta panel.
- See `docs/operations/runbooks/beta-dev-admin-panel.md`.

## Dev UI preview route (current)
- Route: `/dev/kiosk-preview`
- Purpose: develop kiosk UI without QR scan, backend polling, machine hardware, or Shelly triggers.
- Scenario source: `frontend/src/kiosk/dev/kioskPreviewScenarios.js`
- Real UI rendering path: `frontend/src/kiosk/KioskRouter.jsx`
- URL scenario examples:
  - `/dev/kiosk-preview?scenario=scan-screen`
  - `/dev/kiosk-preview?scenario=touch-only-select-machine`
  - `/dev/kiosk-preview?scenario=touch-and-button-box-select-machine`
  - `/dev/kiosk-preview?scenario=machine-in-use`
  - `/dev/kiosk-preview?scenario=backend-unreachable`

## Overview
- QR codes are generated per order and stored in SQLite (`codes.db`).
- A background listener accepts scans from a USB serial scanner (or manual input fallback) and records every attempt to `scan_logs`.
- Devices and machines are modeled in the database; telemetry polling drives per-machine availability and start confirmation.
- Successful, confirmed starts pulse Shelly UNI relays, decrement the code usage counter, and reset the kiosk to the idle scan prompt.
- A touchscreen frontend polls the backend every second to mirror UI state.
- Administrative endpoints enable code management, audit logs, settings, and telemetry diagnostics.

## Repository Layout
- `backend/` Flask application, controllers, models, setup scripts, and logging utilities.
- `backend/setup/seed_machines.py` Seeds devices/machines/config with default Shelly inventory.
- `frontend/` Vite + React kiosk application.
- `docs/` Structured documentation hub (architecture, operations, integrations, and project backlog).
- `Testing_Files/` Ad hoc test scripts, HTTP collections, and database viewers.
- `requirements.txt` Backend Python dependencies.

## Read this next (operator-critical docs)
- Install/bootstrap runbook: `docs/operations/runbooks/install-and-bootstrap.md`
- Update/upgrade runbook: `docs/operations/runbooks/update-and-upgrade.md`
- Recovery/rollback runbook: `docs/operations/runbooks/recovery-and-rollback.md`
- Troubleshooting matrix: `docs/operations/runbooks/troubleshooting-matrix.md`
- Runtime lifecycle: `docs/architecture/runtime-lifecycle.md`
- Settings catalog: `docs/reference/settings-catalog.md`
- API reference: `docs/reference/api-reference.md`
- Database schema/lifecycle: `docs/reference/database-schema-and-lifecycle.md`
- Scripts/tools reference: `docs/reference/scripts-and-tools.md`
- Runtime/process management: `docs/operations/runbooks/runtime-and-process-management.md`
- Reisa operator playbook: `docs/integrations/reisa/runbooks/reisa-operator-playbook.md`
- AI orientation layer: `docs/ai/README.md`

## Quick Start
All commands assume the repository root as the working directory.

### Backend (Flask API + hardware listeners)
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend.setup.seed_settings
python -m backend.setup.seed_machines
python -m backend.app
```
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.setup.seed_settings
python -m backend.setup.seed_machines
python -m backend.app
```
The backend starts on port 5000, launches the touchscreen API, schedules code cleanup, starts telemetry polling, and begins listening for QR scans.

### Frontend (React kiosk)
```bash
cd frontend
npm install
npm run dev
```
The Vite dev server runs on port 3000 and proxies `/api` requests to the backend.

### Retrieve the API key
The kiosk and external devices must send the `X-API-KEY` header. Generate or fetch the key with:
```bash
python -m backend.setup.seed_settings   # only needed the first time
python backend/scripts/get_api_key.py
```
Configure the touchscreen UI by storing the key in `localStorage` (press F12 in the kiosk browser and run `localStorage.setItem("API_KEY", "<value>")`). Alternatively, create a `.env` file under `frontend/` with `VITE_API_KEY=<value>` so the build injects the header automatically.

## Data Model
- `codes`: QR codes with order_id, usage limits, and expiration logic.
- `devices`: Single source of truth for Shelly hardware (role, IP, relay/input channels, metric source).
- `machines`: UI-facing machines mapped to UNI/i4 devices plus enable/disable flags.
- `machine_configs`: Per-machine thresholds, debounce, and poll intervals for telemetry-driven state.
- `scan_logs`: Every scan attempt (API or serial) with result metadata.

Run `python -m backend.setup.seed_machines` to populate initial devices and machines; adjust IPs/roles to match your deployment.

## Configuration & Settings
Defaults live in `backend/setup/seed_settings.py` and are persisted in the `settings` table. Key entries:

| Key | Purpose | Default |
| --- | --- | --- |
| `cors_allowed_origins` | Comma-separated list for browser access | `http://localhost` |
| `admin_username` / `admin_password_hash` | Credentials for admin endpoints | `admin` / SHA-256(`admin`) |
| `api_key` | Kiosk/API authentication key | generated at first run |
| `log_level` | Global log level (overridden by `LOG_LEVEL` env) | `INFO` |
| `button_select_timeout_sec` | Timeout for waiting on i4 button selection after a scan | `45` |
| `button_box_enabled` | Enables optional button-box selection input (`true/1/yes/on`) | `false` |

Use `backend/models/setting_model.py:update_setting_value` or the admin REST endpoints to modify values.

## API Surface
Public endpoints require `X-API-KEY` unless noted otherwise.

| Endpoint | Method | Description |
| --- | --- | --- |
| `/generate_code` | POST | Create a new QR code for an order. Body: `order_id`, `usage_limit`. |
| `/api/scan_code` | POST | Validate a scanned code, arm it for selection, and return machine availability. Writes to `scan_logs`. |
| `/api/start_machine` | POST | Trigger a machine start for the provided code/machine_id; debit occurs after telemetry confirms. |
| `/api/touch_select_machine` | POST | Start selected machine from touchscreen during `choose_machine` using active backend scan/session context. |
| `/api/i4_event` | POST | Receive optional button-box i4 input (accepted only when `button_box_enabled=true`) and start mapped machine for the armed code. |
| `/api/ui_state` | GET | Poll current UI state for the kiosk (includes machine snapshot). |
| `/admin/codes` | GET | List all codes (admin auth required). |
| `/admin/codes/<code>` | GET/DELETE | Inspect or delete a single code. |
| `/admin/codes/by_order_id/<order_id>` | GET/DELETE | Manage codes tied to an order. |
| `/admin/usage/...` | GET | Inspect scan logs by order, code, or most recent. |
| `/admin/settings/<key>` | GET/PUT | Retrieve or update settings. |
| `/admin/settings/cors` | PUT | Overwrite allowed CORS origins (JSON body `{ "origins": [...] }`). |
| `/admin/scan_logs/last/<N>` | GET | Inspect recent scan attempts. |

Admin routes enforce HTTP Basic auth using the credentials stored in the `settings` table. Always rotate the default password before exposing the service.

## Touchscreen & Hardware Flow
1. `waiting_for_code` - Idle screen instructing the user to scan.
2. `choose_machine` - Displays configured machines and telemetry-backed availability; users can tap an available machine to continue.
3. `machine_starting` - A start pulse was sent; telemetry confirmation will debit usage and return UI to idle.
4. `error` - Signals invalid codes, selection timeouts, or hardware failures; auto-resets to idle.

Machine definitions are read from the database (not hard-coded). Telemetry polling tracks UNI metrics and marks machines available/in_use/offline for UI badges and start gating.

## Background Jobs & Hardware
- **Telemetry poller** (`backend/controllers/telemetry.py`) queries UNI devices on intervals from `machine_configs`, applies thresholds/debounce, and emits run-state events.
- **Scanner loop** (`backend/controllers/qr_scanner.listen_for_scans`) consumes serial data and logs every attempt to `scan_logs` (with a keyboard fallback).
- **Shelly integration** (`backend/utils/shelly_control.py`) can pulse, turn on, or turn off relays; device IPs/channels are read from the `devices` table.
- **Cleanup scheduler** (`backend/app.py`) runs every 24 hours to purge expired codes and associated scan logs.

## Logging & Diagnostics
- Logs are stored at `backend/logs/app.log` with rotation (10 MB, 5 backups) and mirrored to stdout.
- Event names include `SCAN received`, `START_PULSE_SENT`, `RUNSTATE_STARTED/STOPPED`, `BUTTON_BOX_ON/OFF`, and telemetry health markers.
- Set `LOG_LEVEL` before launching the backend to override the stored setting (`export LOG_LEVEL=INFO`).
- Use `sqlite3 codes.db` commands for database inspection (see `docs/reference/database-schema-and-lifecycle.md`).
- Sample HTTP flows are available under `Testing_Files/*.http` (compatible with VS Code REST Client and Insomnia).

## Testing & Tooling
- Python unit tests (default): `python -m unittest discover backend/tests`.
- Legacy utility scripts remain in `Testing_Files/` (API samples, DB viewer).
- Logging smoke test: `python -m unittest backend.tests.test_logger`.
- Serial reader exercise: `python -m backend.controllers.qr_scanner` (adjust COM/TTY port).
- Frontend linting/formatting can be added with `npm run lint` once a config is introduced (Prettier is included as a dev dependency).

Backend regression checks:
- `python -m pytest backend/tests/test_ui_api.py`
- `python -m pytest backend/tests/test_machine_control.py`
- `python -m pytest backend/tests/test_flask_startup_bootstrap.py`

Frontend preview checks:
- `cd frontend && npm run dev`
- Open `/dev/kiosk-preview` and scenario URLs listed above.

## Troubleshooting
- Confirm the backend created `codes.db` in the repository root. Deleting it will reset all codes, settings, device inventory, and machine configs (rerun seed scripts afterward).
- If the kiosk shows "Invalid API key", reseed settings and update the key stored in the browser.
- Serial scanners on Windows usually appear as `COM#`. Update the serial port in your hardware configuration.
- Enable debug logging (`LOG_LEVEL=DEBUG`) to capture serial failures, Shelly responses, and telemetry reads.

## Maintenance Notes
- Track open bugs, follow-ups, and future optimizations in `docs/project/future/backlog.md`. Update entries as fixes land; do not implement a suggestion until it is confirmed with the project owner.
- Seed device and machine rows via `python -m backend.setup.seed_machines` whenever a new database is created or hardware inventory changes.
- Replace placeholder IPs and button mappings in `backend/setup/seed_machines.py` before field trials.
- Consider migrating to SQLAlchemy `scoped_session` or per-thread sessions before deploying multi-threaded or production workloads.
