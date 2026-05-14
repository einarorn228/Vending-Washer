# Troubleshooting Matrix

## Purpose
Fast incident guide: **symptom → likely cause → where to check → what to do next**.

Use this during outages or failed setup/update validation.

---

## Rapid incident triage first steps
1. Confirm backend process is running (`python -m backend.app` expected for full behavior).
2. Confirm API key correctness (`python backend/scripts/get_api_key.py`).
3. Check `/api/ui_state` first.
4. Tail logs (`backend/logs/app.log`, `events.log`, `errors.log`).
5. If Reisa mode enabled, check `/admin/reisa/sync_failures` early.

---

## Matrix

| Symptom | Likely cause(s) | Where to check | What to do next |
|---|---|---|---|
| `Invalid API key` from `/api/*` | wrong key in header/localStorage/env | `backend/scripts/get_api_key.py`, `settings` table, frontend localStorage | fetch current key, update frontend, retry `/api/ui_state` |
| Admin route returns 401 even with password | missing API key header or bad Basic auth hash | `backend/flask_server.py` auth wrappers, settings `admin_*`, `api_key` | send both `X-API-KEY` and valid Basic auth; rotate/update credentials if needed |
| Backend import/startup crash | dependency drift, syntax/import error, environment mismatch | backend startup terminal, `app.log` | reinstall deps, verify entrypoint, rollback if recent update broke imports |
| Seed scripts appear ineffective | tables already populated; scripts are mostly insert-if-missing | `seed_settings.py`, `seed_machines.py`, DB rows | apply explicit DB updates for existing rows; don’t expect migration behavior |
| DB/session odd behavior | `codes.db` path mismatch, stale DB, session/thread interactions | repo root for `codes.db`, logs, usage session tables | verify working directory, backup DB, restart backend; consider rollback if post-update regression |
| Scanner not working | wrong serial settings/port, serial unavailable at import-time | scanner warnings in logs, `serial_port` setting, `tools/test_scanner.py` | set correct serial settings, restart backend, test port directly |
| Telemetry/device offline | bad IP/metric source, network unreachable, Shelly endpoint mismatch | telemetry logs, `devices`/`machines` rows, hardware reachability | verify device IPs and metric source, network ping/curl Shelly endpoints, adjust DB rows |
| Shelly start failures | `backend_relay_enabled` true with unreachable/misconfigured device | events/errors logs around start, machine runtime config | validate relay-enabled intent, device address/channel, then retry start flow |
| Frontend shows stale/wrong state | backend not reachable, API key mismatch, poll contract mismatch | browser console, `/api/ui_state`, `frontend/src/App.jsx` | verify backend path and key, inspect API payload directly |
| Frontend stuck on "scan code" after valid scan | Chromium caching the `GET /api/ui_state` fetch request | `frontend/src/api/backend.js`, `backend/controllers/ui_api.py` | Ensure `cache: 'no-store'` is in the frontend `fetch` options and `Cache-Control` headers are sent by Flask. |
| Machine stuck in starting/error loop | telemetry confirmation missing, timeout settings too strict, pending state race | `events.log` for `SELECTION_TIMEOUT`/runstate events, timeout settings | tune `selection_timeout_sec` / thresholds, verify telemetry transitions, clear root cause then retry |
| Reisa sync failures increasing | upstream timeout/auth/action mismatch | `/admin/reisa/sync_failures`, audit events categories, retry jobs | fix root cause (token/url/action/network), then replay targeted jobs |
| Replay jobs stuck pending/retrying | worker disabled, due jobs not replayed, repeat transient failures | `/admin/reisa/retry_jobs?due_only=true`, retry worker settings | run manual `/admin/reisa/retry_due`, or enable worker cautiously |
| `BUTTON_BOX_* skipped (backend_relay_enabled=false)` in `events.log` | relay simulation mode; setting is `false` | `settings.backend_relay_enabled`, [`enable_hardware_e2e.py`](../../../backend/setup/enable_hardware_e2e.py) | run `python -m backend.setup.enable_hardware_e2e`, restart backend; confirm intent before enabling real hardware |
| Kiosk / browser UI blank or empty | Vite not running, Chromium GPU quirk, or wrong URL | `ss -tlnp` for port 3000, kiosk script, [`kiosk-and-e2e-testing.md`](./kiosk-and-e2e-testing.md) | start `npx vite --host --port 3000`, try `KIOSK_DISABLE_GPU=0` on Chromium if needed, open `http://localhost:3000` or correct LAN URL |
| UI banner “Ekki náð í bakenda” on Pi only | missing `VITE_API_KEY` / `localStorage` after Chromium profile wipe; or backend down | `frontend/.env`, `get_api_key.py`, port 5000 | add `VITE_API_KEY` to `.env`, restart Vite; ensure `.venv/bin/python -m backend.app` on Pi |
| Odd duplicate scans / flaky UUID | USB framing; see scanner runbook | `app.log` scanner lines, [`hardware-and-scanner-troubleshooting.md`](./hardware-and-scanner-troubleshooting.md) | tune `scan_timeout`, verify baud; read USB fragment mitigation section |

---

## Detailed incident branches

### 1) Invalid/missing API key
Checks:
```bash
python backend/scripts/get_api_key.py
curl -H "X-API-KEY: <KEY>" http://127.0.0.1:5000/api/ui_state
```
If frontend-only issue:
- verify `localStorage.API_KEY` or `frontend/.env` value,
- restart frontend dev server.

### 2) Admin auth failures
Use both:
- `X-API-KEY` header,
- HTTP Basic auth (`admin_username` + `admin_password_hash` equivalent plaintext before hashing).

Example:
```bash
curl -u admin:<password> -H "X-API-KEY: <KEY>" http://127.0.0.1:5000/admin/codes
```

### 3) Startup/import failures
- run backend directly to capture stack trace:
```bash
python -m backend.app
```
- verify dependency install:
```bash
pip install -r requirements.txt
```
- if update-related and urgent, execute rollback runbook.

### 4) Seed/bootstrap issues
- verify table contents:
```bash
sqlite3 codes.db "SELECT key,value FROM settings ORDER BY key;"
sqlite3 codes.db "SELECT code,order_id,usage_limit,current_usage,expiration_date FROM codes LIMIT 5;"
```
- remember `seed_machines` does not overwrite existing machines automatically.

### 5) DB/session issues
- confirm single expected DB file at repo root.
- backup before invasive changes:
```bash
cp codes.db codes.db.debug.bak
```
- if corruption suspected, restore known-good DB snapshot.

### 6) Scanner not working
- direct serial test:
```bash
python tools/test_scanner.py
```
- set `serial_port` correctly for host OS/device.
- restart backend after changing scanner settings.

### 7) Telemetry/device offline
- inspect machine snapshot:
```bash
curl -H "X-API-KEY: <KEY>" http://127.0.0.1:5000/api/ui_state
```
- check logs for `TELEMETRY_READ` and `DEVICE_OFFLINE`.
- verify per-machine threshold configs and metric source compatibility.

### 8) Shelly failures
- check whether backend relay control is intentionally enabled:
  - setting `backend_relay_enabled`
- inspect event/error logs for relay command failures.
- validate device IP and relay channel mapping in DB.

### 9) Frontend/backend mismatch
- frontend polls every second; backend is source of truth.
- inspect browser console and raw `/api/ui_state` payload side-by-side.
- confirm frontend proxy (`frontend/vite.config.mjs`) still targets `localhost:5000`.

### 10) Reisa sync/retry/replay problems
Core commands:
```bash
curl -u admin:<password> -H "X-API-KEY: <KEY>" http://127.0.0.1:5000/admin/reisa/sync_failures
curl -u admin:<password> -H "X-API-KEY: <KEY>" "http://127.0.0.1:5000/admin/reisa/retry_jobs?limit=100"
curl -X POST -u admin:<password> -H "X-API-KEY: <KEY>" http://127.0.0.1:5000/admin/reisa/retry_due
```
Use Reisa operator playbook for safe sequence and anti-patterns.

---

## Escalation rule of thumb
Escalate to rollback when:
- start flow reliability is uncertain,
- external sync correctness is uncertain,
- repeated troubleshooting cycles do not stabilize within acceptable downtime.

See [`recovery-and-rollback.md`](./recovery-and-rollback.md).

---

## Related docs
- Install/bootstrap: [`install-and-bootstrap.md`](./install-and-bootstrap.md)
- Update/upgrade: [`update-and-upgrade.md`](./update-and-upgrade.md)
- Recovery/rollback: [`recovery-and-rollback.md`](./recovery-and-rollback.md)
- Reisa operator playbook: [`../../integrations/reisa/runbooks/reisa-operator-playbook.md`](../../integrations/reisa/runbooks/reisa-operator-playbook.md)
