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

## 5.1) Kiosk UI preview (dev-only, no hardware required)

Use this when iterating UI safely without scanner, backend polling, or machine hardware.

```bash
cd frontend
npm run dev
```

Open:
- `/dev/kiosk-preview`
- `/dev/kiosk-preview?scenario=scan-screen`
- `/dev/kiosk-preview?scenario=touch-only-select-machine`
- `/dev/kiosk-preview?scenario=touch-and-button-box-select-machine`
- `/dev/kiosk-preview?scenario=machine-in-use`
- `/dev/kiosk-preview?scenario=backend-unreachable`

Key behavior notes:
- The preview uses fake scenario payloads from `frontend/src/kiosk/dev/kioskPreviewScenarios.js`.
- Rendering still uses the real kiosk UI routing path via `frontend/src/kiosk/KioskRouter.jsx`.
- UI component/style edits affect both production kiosk UI and this preview route.
- Backend/API behavior changes affect normal kiosk mode unless equivalent mock updates are added to preview scenarios.

---

## 5.2) Backend + input architecture regression checks

Backend test commands:

```bash
python -m pytest backend/tests/test_ui_api.py
python -m pytest backend/tests/test_machine_control.py
python -m pytest backend/tests/test_flask_startup_bootstrap.py
```

Manual behavior checklist:
- With `button_box_enabled=false`:
  - touchscreen selection still works in `choose_machine`
  - `/api/i4_event` rejects button input
  - button box is not activated after scan
- With `button_box_enabled=true`:
  - touchscreen selection still works
  - button-box input works if a valid scan/session is active
- With no valid scan/session:
  - touch and button-box starts fail safely
- With busy/unavailable machine:
  - touch and button-box starts fail safely

---

## 5.3) Staged pre-beta hardware verification

Run this before beta, in order. **Stage A actuates nothing** -- `backend_relay_enabled`
stays `false` throughout, so no relay can fire. Only Stage B moves hardware, one machine at
a time. Do not start Stage B until every Stage A step passes.

Confirm you are in a safe state before starting:

```bash
source .venv/bin/activate
sqlite3 codes.db "SELECT key,value FROM settings WHERE key='backend_relay_enabled';"
```

Expected: `backend_relay_enabled|false`.

### Stage A -- no hardware actuation

| # | Step | Pass condition |
|---|------|----------------|
| A1 | `source .venv/bin/activate && python -m backend.app` | Starts clean; telemetry thread up; no import errors |
| A2 | Open `/dev/admin`, unlock | Every tab loads: Overview, Remote Control, Diagnostics, Settings, Machine Cards |
| A3 | Machine Cards -- check mappings against the live DB (query below) | Shelly IP, relay channel and I4 button index correct for all four machines |
| A4 | Machine Cards -- rename two cards, reorder, set one name empty, Save | **Nothing** saves; per-row error; all cards unchanged |
| A5 | Fix the empty name, Save again | All changes apply together; order updates |
| A6 | Diagnostics -- Live readings, machines idle | Values update ~1/s; chart draws; readings sit below the OFF threshold |
| A7 | Diagnostics -- switch to Scan log / Change history / Metrics | Live polling stops; Pi load settles |
| A8 | Diagnostics -- confirm units per machine | Washer 1 / Dryer 1 report **voltage**, Washer 2 / Dryer 2 report **power**; thresholds are all 8/3, so confirm that is right for both metrics |
| A9 | Settings -- change a low-risk timing, review the diff, save | OLD -> NEW shown; value applies without restart |
| A10 | Reisa connectivity (read-only, no start/complete sync) | See below |
| A11 | Scan a real code with relays still disabled | Kiosk advances to machine selection; no relay clicks |

Reisa read-only connectivity check for A10 -- this only reaches the base URL, it does not
start or complete a session:

```bash
source .venv/bin/activate
python - <<'REISA'
from backend.models import Session
from backend.models.setting_model import get_setting_value
s = Session()
try:
    base = get_setting_value(s, "reisa_base_url") or ""
    token = get_setting_value(s, "reisa_bearer_token") or ""
finally:
    s.close()
print("reisa_base_url:", base or "(EMPTY - configure first)")
print("reisa_bearer_token:", "set" if token else "(NOT SET - configure first)")
REISA
```

If either is empty, configure Reisa (section 3) before continuing. Do not print the token.

Authoritative mapping query (used by A3 and B1):

```bash
sqlite3 codes.db "SELECT m.name, m.ui_name, d.ip, m.uni_relay_channel, m.i4_button_index, m.is_enabled \
  FROM machines m JOIN devices d ON d.id = m.uni_device_id ORDER BY m.id;"
```

### Stage B -- controlled single-machine actuation

Stage B fires real relays. One machine per pass, and verify the mapping immediately before
enabling actuation.

| # | Step | Pass condition |
|---|------|----------------|
| B1 | Re-read the mapping for the **one** machine under test (name -> Shelly IP -> relay channel) | Matches the query below and the physical label on the unit |
| B2 | Physically confirm which unit that IP is wired to | You can point at the machine that should move |
| B3 | Enable actuation: set `backend_relay_enabled = true` in `/dev/admin` -> Settings (acknowledge the warning) | Saved; applies without restart |
| B4 | Scan a code and select **only** that machine | The expected physical machine energises; no other unit reacts |
| B5 | Check the kiosk copy | Reservation window matches `machine_reservation_minutes` |
| B6 | Diagnostics -- watch the machine run | Reading rises above the ON threshold; "Above for" climbs; state becomes in-use |
| B7 | Let the machine finish, or stop it | Reading drops below OFF threshold; kiosk returns to waiting |
| B8 | Repeat B1-B7 for the next machine | One at a time; never two in the same pass |
| B9 | Only if a pulse looks wrong: change `relay_pulse_duration_sec`, retest, then **restore the original value** | Documented in Diagnostics -> Change history |
| B10 | When finished, restore any temporary tuning changes | Change history shows the value back at its intended setting |
| B11 | Decide the end state for `backend_relay_enabled` | Left `true` for beta, or back to `false` for bench work -- deliberately, not by accident |

If Dryer 2 (`192.168.107.14`) or the i4 box does not respond, confirm the device is on the
network before treating it as a software fault -- both have been offline before.

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
