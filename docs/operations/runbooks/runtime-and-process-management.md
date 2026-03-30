# Runtime and Process Management Runbook

This is the operational runbook for starting, stopping, restarting, and health-checking runtime processes.

Source of truth:
- `backend/app.py`
- `backend/flask_server.py`
- `frontend/package.json`
- `frontend/scripts/open-pi-browser.sh`
- `backend/controllers/qr_scanner.py`

## Process ownership summary

## Backend full runtime (recommended)
Command:
```bash
python -m backend.app
```

Starts:
- Flask server thread (`0.0.0.0:5000`, debug true, no reloader)
- telemetry polling thread
- cleanup scheduler thread
- Reisa retry worker thread (settings-gated behavior)
- scanner listener thread (only if serial is available)

## Flask-only runtime (limited)
Command:
```bash
python -m backend.flask_server
```

Important:
- This starts Flask routes only.
- It does not start the same background worker set as `backend.app`.

## Frontend runtime
Command:
```bash
cd frontend
npm run dev
```

Important side effect:
- current `npm run dev` also executes Pi browser opener script.
- opener script is Pi-user/path specific and launches Chromium twice.

## Safe startup procedure
1. Activate backend virtualenv (root `.venv` convention).
2. Start backend via `python -m backend.app`.
3. Wait for startup logs.
4. Verify `/api/ui_state` with API key.
5. Start frontend.

Commands:
```bash
source .venv/bin/activate
python -m backend.app
```

In second terminal:
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
```

Then:
```bash
cd frontend
npm run dev
```

## Safe restart procedure
1. Stop frontend and backend processes.
2. Backup DB if restart follows config/schema-sensitive changes.
3. Restart backend first, verify health, then frontend.

Suggested stop commands:
```bash
pkill -f "python -m backend.app" || true
pkill -f "vite --host --port 3000" || true
```

Then start again with safe startup procedure.

## Health checks

## Minimum healthy signals
- `/api/ui_state` returns JSON with `state`, `message`, `machines`.
- `backend/logs/errors.log` has no repeating fresh exceptions.
- `events.log` shows expected flow events during test scan/start.

## Command checks
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
```

```bash
tail -n 100 backend/logs/app.log
```

```bash
tail -n 100 backend/logs/errors.log
```

## Runtime gotchas

## Startup overlap
Both `backend/app.py` and `backend/flask_server.py` perform initialization/bootstrap actions. This overlap exists today and must be considered during process changes.

## Scanner import-time behavior
`backend/controllers/qr_scanner.py` reads serial settings and opens serial at import time. Scanner setting changes require backend restart.

## Virtualenv mismatch
`run-backend.sh` expects `backend/.venv`, while most docs and workflows use root `.venv`.

## High-risk operation
Starting only `backend.flask_server` and assuming full machine-control behavior is active.

## Requires restart
- scanner setting changes (`serial_port`, `serial_baudrate`, `scan_timeout`)
- logger-level changes for consistent effect
- CORS behavior changes for consistent effect

## Unknown / requires verification from code
- No repository-provided systemd/supervisor unit files are present for production process management.
