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
Status: Supported on the intended Raspberry Pi kiosk host

Behavior (current):
- launches a **single** Chromium or `chromium-browser` instance in kiosk mode,
- optional `KIOSK_URL` (default `http://localhost:3000/`),
- optional `KIOSK_DISABLE_GPU` (default enables `--disable-gpu` for blank-window mitigation on some Pi stacks).

Gotchas:
- hardcoded X11 paths for user `hamrar` — adjust on other accounts.

See also: [`../operations/runbooks/kiosk-and-e2e-testing.md`](../operations/runbooks/kiosk-and-e2e-testing.md).

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

## `backend/setup/configure_reisa.py`
Status: Supported

Purpose:
- writes Reisa provider settings into `settings` (`provider_default`, `provider_reisa_enabled`, `reisa_base_url`, `reisa_bearer_token`, action names).

Commands:
```bash
export REISA_BEARER_TOKEN='…'
python -m backend.setup.configure_reisa
python -m backend.setup.configure_reisa --full-stack
```

`--full-stack` additionally enables `backend_relay_enabled`, `telemetry_enabled`, `reisa_retry_worker_enabled`, and expands `cors_allowed_origins` for local Vite/kiosk. Optional: `CORS_EXTRA_ORIGINS`, `--cors-origins`, `--base-url`, `--dry-run`.

Restart backend after CORS changes.

## `backend/setup/enable_hardware_e2e.py`
Status: Supported

Purpose:
- set `backend_relay_enabled=true`, `telemetry_enabled=true`, and `scan_timeout=3` for real Shelly/button-box testing (does **not** change Reisa secrets).

Command:
```bash
python -m backend.setup.enable_hardware_e2e
```

Restart backend after running (serial `scan_timeout` is applied when the scanner port opens).

See: [`../operations/runbooks/kiosk-and-e2e-testing.md`](../operations/runbooks/kiosk-and-e2e-testing.md).

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

See also:
- Newland FM3080 USB CDC on Pi: [`../operations/runbooks/scanner-newland-fm3080-cdc.md`](../operations/runbooks/scanner-newland-fm3080-cdc.md)

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

Warning:
- these files are not authoritative operational examples,
- they may omit current required auth headers and modern runbook safety guidance.

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
