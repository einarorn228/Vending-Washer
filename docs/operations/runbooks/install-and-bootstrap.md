# Install and Bootstrap Runbook

## Purpose
Use this runbook for a **fresh setup** of the Vending Washer repository on a development workstation, kiosk test box, or staging-like host.

This guide is optimized for:
- owners/admins who need reliable first bring-up,
- less experienced operators who need exact command order,
- AI assistants that need deterministic setup flow.

If you already have a working install and are updating, use [`update-and-upgrade.md`](./update-and-upgrade.md) instead.

---

## What this repo runs
- Backend: Flask API + scanner listener + telemetry poller + cleanup scheduler + optional Reisa retry worker (`python -m backend.app`).
- Frontend: React/Vite touchscreen UI on port 3000 (`npm run dev`).
- Database: SQLite file `codes.db` created in repo root.

---

## Prerequisites

### Required software
- Python 3.10+ (3.11 recommended)
- Node.js 18+
- npm 9+
- Git

### Hardware/integration dependencies (optional for initial software bring-up)
- USB serial scanner (or skip and use API scan endpoint)
- Shelly devices reachable on network for relay/telemetry tests
- Reisa credentials only if enabling Reisa provider mode

### Network/host notes
- Backend binds to `0.0.0.0:5000` when started from `backend.app`.
- Frontend dev server is `http://localhost:3000` and proxies `/api` to backend.

---

## 1) Clone and enter repository
```bash
git clone <YOUR_REPO_URL>
cd Vending-Washer
```

---

## 2) Python virtualenv + backend dependencies

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Windows PowerShell
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> Note: `run-backend.sh` expects `backend/.venv/bin/activate`, but README/setup uses root `.venv`. Prefer the root `.venv` flow above unless you intentionally standardize differently.

---

## 3) Node dependencies (frontend)
```bash
cd frontend
npm install
cd ..
```

---

## 4) Seed/bootstrap database and settings
Run these from repo root with the Python virtualenv active:

```bash
python -m backend.setup.seed_settings
python -m backend.setup.seed_machines
```

What these do:
- create/populate `settings` defaults,
- create API key if missing,
- seed default device/machine inventory only when tables are empty.

---

## 5) Retrieve API key
```bash
python backend/scripts/get_api_key.py
```

Save this value securely. The UI and API routes require `X-API-KEY`.

---

## 6) Configure frontend API key
Choose one method:

### Option A (recommended for local dev): localStorage
Open browser dev tools and run:
```js
localStorage.setItem("API_KEY", "<PASTE_KEY>")
```

### Option B: `frontend/.env`
Create `frontend/.env`:
```env
VITE_API_KEY=<PASTE_KEY>
VITE_API_BASE_URL=
```

`VITE_API_BASE_URL` can stay blank for local proxy usage.

---

## 7) First startup (backend then frontend)

### Terminal 1: backend
```bash
# with venv active from repo root
python -m backend.app
```

Expected behavior:
- logger initializes,
- DB/init/seed/bootstrap checks run,
- Flask starts on port 5000,
- telemetry poll thread starts,
- cleanup scheduler thread starts,
- optional retry worker thread starts but is settings-gated,
- scanner listener starts if serial is available.

High-risk startup note:
- for first bring-up, use `python -m backend.app` (not `python -m backend.flask_server`).
- Flask-only startup does not run settings bootstrap and does not ensure `backend_relay_enabled` row creation.

### Terminal 2: frontend
```bash
cd frontend
npm run dev
```

Frontend expected at `http://localhost:3000`.

For **Raspberry Pi kiosk**, Reisa, Shelly relays, and “real user” testing in one place, follow **[`kiosk-and-e2e-testing.md`](./kiosk-and-e2e-testing.md)** (API key in `frontend/.env`, enable hardware script, single-backend hygiene).

---

## 8) First verification checklist (must pass)

### A. Backend health via UI state
```bash
curl -H "X-API-KEY: <PASTE_KEY>" http://127.0.0.1:5000/api/ui_state
```
Expected: JSON with at least `state`, `message`, and `machines`.

### B. Generate a test code
```bash
curl -X POST \
  -H "X-API-KEY: <PASTE_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"order_id":"INSTALL-SMOKE-001","usage_limit":1}' \
  http://127.0.0.1:5000/generate_code
```

### C. Verify admin auth path
```bash
curl -u admin:admin -H "X-API-KEY: <PASTE_KEY>" http://127.0.0.1:5000/admin/codes
```
If this works, immediately rotate admin password hash via settings endpoint/process.

### D. Check DB file exists
```bash
# macOS/Linux
ls -l codes.db

# PowerShell
Get-Item .\codes.db
```

### E. Optional scanner serial sanity
```bash
python tools/test_scanner.py
```

---

## 9) Common install mistakes (and fixes)

### Mistake: `Invalid API key` everywhere
- Cause: frontend not configured with current key, or wrong header in curl.
- Fix:
  1. `python backend/scripts/get_api_key.py`
  2. update localStorage/`.env`
  3. retry `/api/ui_state`.

### Mistake: backend starts but scanner listener says unavailable
- Cause: serial device missing/locked/wrong port.
- Fix:
  - set `serial_port`, `serial_baudrate`, `scan_timeout` in settings,
  - verify OS serial device path,
  - restart backend.

### Mistake: frontend loads but cannot reach backend
- Cause: backend not running on 5000 or proxy mismatch.
- Fix:
  - verify backend terminal logs,
  - call `curl http://127.0.0.1:5000` route(s),
  - keep `vite.config.mjs` proxy and backend port aligned.

### Mistake: hardware appears unavailable after seed
- Cause: seeded default IPs are placeholders for many environments.
- Fix:
  - update `devices` rows (or seed file for new DBs),
  - verify Shelly device IP reachability,
  - restart backend after config adjustments.

### Mistake: using `run-backend.sh` without matching venv path
- Cause: script expects `backend/.venv` while docs use root `.venv`.
- Fix:
  - start with `python -m backend.app` in activated root `.venv`, or
  - align script and local environment convention.

---

## 10) Post-install hardening (do immediately)
1. Change default admin credentials (`admin` / SHA256(`admin`)).
2. Restrict CORS origins via `/admin/settings/cors`.
3. Set explicit log level and provider mode in settings.
4. If Reisa is not used, keep `provider_reisa_enabled=false`.
5. Record local runbook outputs (API key location, host/IP mapping, machine map).

---

## Related docs
- Update flow: [`update-and-upgrade.md`](./update-and-upgrade.md)
- Recovery/rollback: [`recovery-and-rollback.md`](./recovery-and-rollback.md)
- Troubleshooting matrix: [`troubleshooting-matrix.md`](./troubleshooting-matrix.md)
- Runtime lifecycle internals: [`../../architecture/runtime-lifecycle.md`](../../architecture/runtime-lifecycle.md)
- Settings catalog: [`../../reference/settings-catalog.md`](../../reference/settings-catalog.md)
