# Runtime and Process Management Runbook

This is the operational runbook for starting, stopping, restarting, and health-checking runtime processes.

Source of truth:
- `backend/app.py`
- `backend/flask_server.py`
- `frontend/package.json`
- `frontend/scripts/open-pi-browser.sh`
- `backend/controllers/qr_scanner.py`

## Process ownership summary

Processes started manually in an SSH session or a desktop terminal are tied to that **login session**. When the session ends (logout, laptop sleep, SSH disconnect, closing the terminal window), **systemd-logind** typically tears down the session scope and **stops child processes**. That can look like a mysterious overnight shutdown even though nobody intentionally stopped the app.

For development this is fine. For **production** and for **systems sold to customers**, treat session-bound processes as temporary.

## Production persistence (do this before go-live)

Not implemented in-repo yet; capture this checklist when you are ready to ship or hand off hardware.

1. **Prefer systemd (or an equivalent supervisor)**  
   - Run backend (`python -m backend.app` or `run-backend.sh`) under a **system** or **user** unit with `Restart=on-failure` or `Restart=always` and a sane `RestartSec=`.  
   - If using **user** units on a headless Pi, enable **lingering** so services survive logout: `loginctl enable-linger <deploy-user>`.

2. **Frontend**  
   - For kiosk/Pi: either a **static build** served by nginx/Caddy (or similar) plus the backend API, or a dedicated unit that runs `npm run dev` / `vite` only if you accept dev-server semantics in the field.  
   - Review `npm run dev` side effects (Pi browser opener); production may want a stripped `npm run` script without kiosk automation.

3. **Logging and support**  
   - Operators should know where logs live (`backend/logs/*.log`) and how to `journalctl -u <unit>` if you move stdout/stderr to the journal.

4. **Lighter alternatives** (acceptable for single-site pilots, weaker for sold systems)  
   - `tmux` / `screen` so SSH can drop without killing the process group.  
   - `nohup … &` / `disown` — simple but easy to misconfigure and hard to support remotely.

5. **Document for the buyer**  
   - How services are named, how to restart after power loss, where the venv and repo live, and that **API keys / DB paths must not be reset** by accidental “fresh clone” reinstalls.

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
- It does not run `bootstrap_settings()` (no first-run API key generation).
- It does not run `ensure_backend_relay_setting_exists()` (relay setting missing-key behavior can differ from full runtime path).

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

## Startup mode delta (settings/auth readiness)
- `backend.app`: includes settings bootstrap and relay-setting ensure behavior.
- `backend.flask_server`: excludes both.
- On fresh settings DB, use `python -m backend.app` first to guarantee API key creation and expected relay-setting row insertion.

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
- No repository-provided systemd/supervisor unit files are present yet; see **Production persistence** above when you add them.
