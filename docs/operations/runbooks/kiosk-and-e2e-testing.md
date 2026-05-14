# Kiosk and End-to-End Hardware Testing

## Purpose
Single runbook for **Raspberry Pi kiosk + full backend + Shelly hardware + Reisa**, aligned with how the repo is run in production-like tests.

Use this when you need:
- a repeatable checklist from “clean processes” to “user can scan and start a machine”,
- to verify **relay actuation** is not accidentally in dry-run mode,
- to align **frontend API key**, **Vite**, and **CORS** with the Pi.

Related docs:
- Install/bootstrap: [`install-and-bootstrap.md`](./install-and-bootstrap.md)
- Hardware/scanner deep dive: [`hardware-and-scanner-troubleshooting.md`](./hardware-and-scanner-troubleshooting.md)
- Reisa operations: [`../../integrations/reisa/runbooks/reisa-operator-playbook.md`](../../integrations/reisa/runbooks/reisa-operator-playbook.md)
- Settings reference: [`../../reference/settings-catalog.md`](../../reference/settings-catalog.md)
- Scripts index: [`../../reference/scripts-and-tools.md`](../../reference/scripts-and-tools.md)

---

## 1) Process hygiene (avoid duplicate backends)

Only **one** full runtime should listen on port **5000**.

```bash
pgrep -af 'backend\.app'
```

If more than one line appears (for example both `python3 -m backend.app` and `.venv/bin/python -m backend.app`), stop extras:

```bash
pkill -f 'python3 -m backend\.app' 2>/dev/null || true
pkill -f '\.venv/bin/python -m backend\.app' 2>/dev/null || true
sleep 2
fuser -k 5000/tcp 2>/dev/null || true
```

Always start the full stack with the **project virtualenv**:

```bash
cd /path/to/Vending-Washer
.venv/bin/python -m backend.app
```

Do **not** use system `python3 -m backend.app` on the Pi unless that interpreter has the same dependencies as `.venv` (it usually does not).

---

## 2) Enable Shelly / button-box actuation (not simulation)

When `backend_relay_enabled` is `false`, events show:

- `BUTTON_BOX_ON skipped (backend_relay_enabled=false)`
- `MACHINE backend relay disabled; skipping Shelly command`

Apply the supported helper (idempotent):

```bash
cd /path/to/Vending-Washer
.venv/bin/python -m backend.setup.enable_hardware_e2e
```

This sets (see script for current list):
- `backend_relay_enabled=true`
- `telemetry_enabled=true`
- `scan_timeout=3` (scanner serial; requires **backend restart** to reopen the port)

Then **restart** `.venv/bin/python -m backend.app`.

Verify in logs or DB:

```bash
sqlite3 codes.db "SELECT key,value FROM settings WHERE key IN ('backend_relay_enabled','telemetry_enabled','scan_timeout');"
```

---

## 3) Reisa + “full stack” settings (optional but common on Pi)

One-shot configuration (token required except in `--dry-run`):

```bash
export REISA_BEARER_TOKEN='…'
.venv/bin/python -m backend.setup.configure_reisa --full-stack
```

`--full-stack` also sets `reisa_retry_worker_enabled=true` and expands `cors_allowed_origins` for local Vite/kiosk. **Restart the backend** after changing CORS so Flask reads the new list.

Optional extra origins (LAN IP of the Pi UI):

```bash
export CORS_EXTRA_ORIGINS='http://192.168.x.x:3000'
.venv/bin/python -m backend.setup.configure_reisa --full-stack
```

See module docstring in `backend/setup/configure_reisa.py` for flags and examples.

---

## 4) Frontend (Vite) and API key on the kiosk host

The UI polls `/api/ui_state` with `X-API-KEY`.

### `frontend/.env` (recommended on the Pi)
```env
VITE_API_KEY=<same value as settings.api_key>
VITE_API_BASE_URL=
```

`VITE_*` variables are read when **Vite starts** — restart Vite after editing `.env`.

### Start Vite
```bash
cd frontend
npm install   # once
npx vite --host --port 3000 --strictPort
```

`npm run dev` also starts Vite but may launch the Pi Chromium helper; for headless debugging, `npx vite …` is enough.

### Kiosk browser (local display)
```bash
bash frontend/scripts/open-pi-browser.sh
```

Optional environment variables are documented in the script header (`KIOSK_URL`, `KIOSK_DISABLE_GPU`).

### After wiping Chromium profile
`localStorage` API key is lost. Prefer `frontend/.env` on the kiosk machine so the key survives profile deletes.

---

## 5) Verification checklist

| Step | Command / action | Expected |
|------|------------------|----------|
| Backend | `curl -H "X-API-KEY: $(.venv/bin/python backend/scripts/get_api_key.py)" http://127.0.0.1:5000/api/ui_state` | HTTP 200 JSON |
| Frontend | `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3000/` | `200` |
| Relay not skipped | Tail `backend/logs/events.log` during armed scan | `BUTTON_BOX_ON` / `BUTTON_BOX_OFF` **without** `skipped` when relay enabled |
| Telemetry | Same log | `TELEMETRY_READ` may still warn if Shelly IPs wrong — fix `devices` rows / network |

---

## 6) Device IPs and topology

Default seeded IPs live in `backend/setup/seed_machines.py`. If your Shellys use another subnet, update the `devices` table (or re-seed on a fresh DB) so telemetry and relays hit real hardware.

Architecture reference: [`../../architecture/hardware-topology-and-telemetry.md`](../../architecture/hardware-topology-and-telemetry.md).

---

## 7) Turning hardware simulation back on

For lab-only runs without firing relays:

```bash
.venv/bin/python - <<'PY'
from backend.models import Session
from backend.models.setting_model import update_setting_value
s = Session()
try:
    update_setting_value(s, "backend_relay_enabled", "false")
finally:
    s.close()
PY
```

Restart the backend after the change.
