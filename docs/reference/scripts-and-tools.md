# Scripts and Tools Reference

This document classifies scripts by operational support status.

Classification rules used here:
- Supported: referenced by current runbooks and aligned with current package paths.
- Legacy: ad hoc or environment-specific scripts that are not reliable defaults.

## Root scripts

## `run-backend.sh`
Path: `run-backend.sh`
Status: Legacy (environment mismatch risk)

Behavior:
- `source backend/.venv/bin/activate`
- runs `python -m backend.app`

Gotcha:
- Most docs use root `.venv`, not `backend/.venv`.
- This script fails unless you created `backend/.venv`.

Safe operation:
```bash
source .venv/bin/activate
python -m backend.app
```

## `run-frontend.sh`
Path: `run-frontend.sh`
Status: Legacy / Pi-host specific

Behavior:
- sets `DISPLAY`, `XAUTHORITY=/home/hamrar/.Xauthority`, `XDG_RUNTIME_DIR`
- runs `npm run dev` in `frontend/`

Gotcha:
- hardcoded user/home assumptions.
- not suitable as generic cross-host launcher.

## Frontend scripts

## `frontend/package.json` scripts

### `npm run dev`
Status: Supported for Pi-like kiosk workflows, but has side effects.

Actual command:
- starts Vite on `--host --port 3000 --strictPort`
- concurrently runs `npm run open:pi`

### `npm run open:pi`
Status: Legacy / Pi-specific helper

Actual command:
- waits for `http://localhost:3000`
- executes `frontend/scripts/open-pi-browser.sh`

### `npm run build`
Status: Supported

### `npm run start`
Status: Supported (preview mode)

## `frontend/scripts/open-pi-browser.sh`
Status: Legacy / Pi-specific

Gotchas:
- Starts Chromium twice (two launch commands in file).
- hardcoded `/home/hamrar/*` paths.

Use only when running on the intended Raspberry Pi environment.

## Backend helper scripts

## `backend/scripts/get_api_key.py`
Status: Supported

Purpose:
- prints `settings.api_key`.

Command:
```bash
python backend/scripts/get_api_key.py
```

## `backend/setup/seed_settings.py`
Status: Supported

Purpose:
- seed missing settings and ensure API key exists.

Command:
```bash
python -m backend.setup.seed_settings
```

## `backend/setup/seed_machines.py`
Status: Supported

Purpose:
- seed devices/machines/config only when related tables are empty.

Command:
```bash
python -m backend.setup.seed_machines
```

High-risk note:
- Not a migration tool.

## `backend/setup/setup_logs.py`
Status: Legacy utility

Purpose:
- creates `backend/logs/app.log` directory/file.

Note:
- current runtime logger setup (`configure_logger`) already ensures targets.

## Tools directory

## `tools/test_scanner.py`
Status: Supported for scanner diagnostics

Purpose:
- direct serial read test using DB-configured serial settings.

Command:
```bash
python tools/test_scanner.py
```

Requires:
- serial device access
- `serial_port`, `serial_baudrate`, `scan_timeout` settings (or defaults)

## Testing_Files directory

These files are legacy/ad hoc and should not be treated as primary operational tooling.

## `Testing_Files/view_db.py`
Status: Legacy

Risk:
- uses `from models ...` imports, which may fail depending on execution path.

Preferred alternative:
- use `sqlite3` CLI commands from `docs/reference/database-schema-and-lifecycle.md`.

## `Testing_Files/update.py`
Status: Legacy / unsafe for routine ops

Behavior:
- hardcoded direct setting update examples.

## `Testing_Files/qr_test.py`
Status: Legacy

Behavior:
- raw serial read loop with hardcoded `/dev/ttyACM0`.

## `Testing_Files/test_api.http`
## `Testing_Files/test_api_get.http`
Status: Legacy but useful as request scratch files.

## Script reality checks

## Verify script inventory
```bash
rg --files run-*.sh backend/scripts backend/setup frontend/scripts tools Testing_Files
```

## Verify frontend command chain
```bash
cat frontend/package.json
cat frontend/scripts/open-pi-browser.sh
```

## Required warnings

- Seed scripts are not migrations.
- Backend has startup overlap between `backend/app.py` and `backend/flask_server.py`.
- Scanner configuration is loaded at import time in `backend/controllers/qr_scanner.py`; changing scanner settings requires backend restart.
- Root launcher virtualenv assumptions are inconsistent.
