# Vending Washer

Touch-first washer vending prototype consisting of a Flask backend, a React touchscreen UI, and hardware integrations for QR scanners and Shelly relays.

## Overview
- QR codes are generated per order and stored in SQLite (`codes.db`).
- A background listener accepts scans from a USB serial scanner (or manual input fallback).
- Successful scans trigger Shelly smart relays to start the configured washer and update the shared UI state.
- A touchscreen frontend polls the backend every second to guide the user through scan, selection, and progress states.
- Administrative endpoints enable code management, audit logs, and configuration tweaks.

## Repository Layout
- `backend/` Flask application, controllers, models, setup scripts, and logging utilities.
- `frontend/` Vite + React kiosk application.
- `scripts/` Utility helpers (currently empty in repo root).
- `Testing_Files/` Ad hoc test scripts, HTTP collections, and database viewers.
- `requirements.txt` Backend Python dependencies.

## Quick Start
All commands assume the repository root as the working directory.

### Backend (Flask API + hardware listeners)
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend.setup.seed_settings
python -m backend.app
```
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.setup.seed_settings
python -m backend.app
```
The backend starts on port 5000, launches the touchscreen API, schedules code cleanup, and begins listening for QR scans.

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
Configure the touchscreen UI by storing the key in `localStorage` (press F12 in the kiosk browser and run `localStorage.setItem("API_KEY", "<value>")`).
Alternatively, create a `.env` file under `frontend/` with `VITE_API_KEY=<value>` so the build injects the header automatically.

## Configuration & Settings
Defaults live in `backend/setup/seed_settings.py` and are persisted in the `settings` table. Key entries:

| Key | Purpose | Default |
| --- | --- | --- |
| `serial_port` | USB device for barcode/QR scanner | `/dev/ttyUSB0` |
| `serial_baudrate` | Baud rate for scanner | `9600` |
| `scan_timeout` | Serial read timeout (seconds) | `1` |
| `shelly_ip` | Default Shelly relay IP used by the scanner listener | `0` (simulate when debug logging enabled) |
| `relay_mode` | `on` or `pulse` mode for Shelly control | `on` |
| `pulse_duration` | Pulse length in seconds (when `relay_mode` is `pulse`) | `1` |
| `code_expiration_days` | Days unused codes remain valid | `0` (no expiry) |
| `expired_code_cleanup_days` | Days after final use before code deletion | `30` |
| `cors_allowed_origins` | Comma-separated list for browser access | `http://localhost, http://173.25.200.254` |
| `admin_username` / `admin_password_hash` | Credentials for admin endpoints | `admin` / SHA-256(`admin`) |
| `log_level` | Global log level (overridden by `LOG_LEVEL` env) | `DEBUG` |

Use `backend/models/setting_model.py:update_setting_value` or the admin REST endpoints to modify values.

## API Surface
Public endpoints require `X-API-KEY` unless noted otherwise.

| Endpoint | Method | Description |
| --- | --- | --- |
| `/generate_code` | POST | Create a new QR code for an order. Body: `order_id`, `usage_limit`. |
| `/api/scan_code` | POST | Touchscreen flow: validate a scanned code and show machine choices. |
| `/api/start_machine` | POST | Start the selected machine and decrement usage. |
| `/api/ui_state` | GET | Poll current UI state for the kiosk. |
| `/admin/codes` | GET | List all codes (admin auth required). |
| `/admin/codes/<code>` | GET/DELETE | Inspect or delete a single code. |
| `/admin/codes/by_order_id/<order_id>` | GET/DELETE | Manage codes tied to an order. |
| `/admin/usage/...` | GET | Inspect scan logs by order, code, or most recent. |
| `/admin/settings/<key>` | GET/PUT | Retrieve or update settings. |
| `/admin/settings/cors` | PUT | Overwrite allowed CORS origins (JSON body `{ "origins": [...] }`). |
| `/admin/scan_logs/last/<N>` | GET | Inspect recent scan attempts. |

Admin routes enforce HTTP Basic auth using the credentials stored in the `settings` table. Always rotate the default password before exposing the service.

## Touchscreen UI Flow
The kiosk is display-only. External hardware triggers API calls; the kiosk mirrors state returned from `/api/ui_state`.

1. `waiting_for_code` - Idle screen instructing the user to scan.
2. `choose_machine` - Displays configured machines and availability.
3. `machine_in_use` - Confirms the washer has started and shows remaining uses.
4. `error` - Signals invalid codes or hardware failures.

`MACHINES` are currently defined in `backend/controllers/machine_control.py` with placeholder IP addresses. Update this mapping to match your deployment.

## Background Jobs & Hardware
- **Scanner loop** (`backend/controllers/qr_scanner.listen_for_scans`) continuously consumes serial data. When the scanner is unavailable the loop falls back to manual console input.
- **Shelly integration** (`backend/utils/shelly_control.py`) turns relays on or issues a configurable pulse. Production deployments should consider per-machine overrides and connection retries.
- **Cleanup scheduler** (`backend/app.py`) runs every 24 hours to purge codes whose `expiration_date` has passed and removes related scan logs.

## Logging & Diagnostics
- Logs are stored at `backend/logs/app.log` with rotation (5 MB, 3 backups) and mirrored to stdout.
- Set `LOG_LEVEL` before launching the backend to override the stored setting (`export LOG_LEVEL=INFO`).
- Use `Testing_Files/view_db.py` for quick database inspection from the command line.
- Sample HTTP flows are available under `Testing_Files/*.http` (compatible with VS Code REST Client and Insomnia).

## Testing & Tooling
- Python unit tests: `python -m unittest discover Testing_Files`.
- Logging smoke test: `Testing_Files/test_logger.py`.
- Serial reader exercise: `Testing_Files/qr_test.py` (adjust the COM/TTY port).
- Frontend linting/formatting can be added with `npm run lint` once a config is introduced (Prettier is included as a dev dependency).

## Troubleshooting
- Confirm the backend created `codes.db` in the repository root. Deleting it will reset all codes and settings.
- If the kiosk shows "Invalid API key", reseed settings and update the key stored in the browser.
- Serial scanners on Windows usually appear as `COM#`. Update `serial_port` accordingly.
- Enable debug logging (`LOG_LEVEL=DEBUG`) to capture serial failures and Shelly responses.

## Maintenance Notes
- Track open bugs, follow-ups, and future optimizations in `issues and sejections.txt`. Update entries as fixes land; do not implement a suggestion until it is confirmed with the project owner.
- Consider migrating to SQLAlchemy `scoped_session` or per-request sessions before deploying multi-threaded or production workloads.
- Replace placeholder machine definitions and hard-coded API keys prior to field trials.


