# Update and Upgrade Runbook

## When to use this guide
Use this guide when an environment is **already installed** and you need to safely apply repository updates.

Use [`install-and-bootstrap.md`](./install-and-bootstrap.md) for brand-new setups.

---

## Pre-update checklist (do not skip)
1. Confirm current system status:
   - backend serving `/api/ui_state`
   - frontend reachable
   - key hardware responding (if applicable)
2. Capture current commit:
   ```bash
   git rev-parse --short HEAD
   ```
3. Backup `codes.db` before update:
   ```bash
   cp codes.db "codes.db.preupdate.$(date +%Y%m%d-%H%M%S).bak"
   ```
4. Record critical settings values:
   ```bash
   sqlite3 codes.db "SELECT key,value FROM settings ORDER BY key;"
   ```
5. Ensure you can restore previous commit (`git reflog` / branch strategy).

---

## Safe update flow

### 1) Stop running services
Stop backend/frontend terminals or service wrappers first.

### 2) Pull latest code
```bash
git fetch origin
git pull --ff-only
```

If fast-forward fails, resolve branch strategy intentionally (do not force pull blindly).

### 3) Refresh backend dependencies

#### macOS/Linux
```bash
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Windows PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4) Refresh frontend dependencies
```bash
cd frontend
npm install
cd ..
```

### 5) Re-run safe bootstrap scripts
```bash
python -m backend.setup.seed_settings
python -m backend.setup.seed_machines
```

These are idempotent for existing rows and ensure missing keys/devices are populated.

### 6) Start backend and frontend
```bash
python -m backend.app
```
In another terminal:
```bash
cd frontend
npm run dev
```

---

## Validation after update

### API and auth checks
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/settings/log_level
```

### Code flow smoke check
```bash
curl -X POST -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d '{"order_id":"UPDATE-SMOKE-001","usage_limit":1}' \
  http://127.0.0.1:5000/generate_code
```

### Test suite smoke (backend)
```bash
python -m unittest discover backend/tests
```

### Reisa diagnostics endpoint smoke (even if local mode)
```bash
curl -u admin:<password> -H "X-API-KEY: $API_KEY" \
  http://127.0.0.1:5000/admin/reisa/sync_failures
```

---

## Detecting partial/bad updates

Signs of partial update:
- backend imports fail after pull,
- frontend runs but `/api/ui_state` fails auth/route,
- admin endpoints respond but machine state never updates,
- Reisa endpoints exist but retry/diagnostics fail unexpectedly.

Checkpoints:
1. `git status` must be clean (unless intentional local overrides).
2. dependency install logs show no unresolved packages.
3. `codes.db` exists and contains expected tables.
4. backend logs show telemetry/scanner/retry worker startup messages.

---

## Seed/bootstrap considerations during upgrade
- `seed_settings` only fills missing keys; it does not necessarily revert changed settings.
- `seed_machines` only seeds when tables are empty; existing machine/device drift remains.
- changing default seed files does **not** automatically mutate existing DB rows.

Operational implication: if release notes rely on new machine/config defaults, apply explicit DB changes or reseed in controlled fashion.

---

## Known drift risks in this repo
1. `run-backend.sh` virtualenv path (`backend/.venv`) differs from README/root setup (`.venv`).
2. Frontend kiosk launcher script currently invokes Chromium twice.
3. Legacy helper scripts under `Testing_Files/` are useful but not all follow current package import conventions equally.
4. Startup responsibilities span `backend/app.py` and `backend/flask_server.py`; see runtime lifecycle doc before changing entrypoint behavior.

---

## If update validation fails
Use [`recovery-and-rollback.md`](./recovery-and-rollback.md).

Minimum emergency actions:
1. stop services,
2. return to previous known-good commit,
3. restore `codes.db` backup if data/state corruption is suspected,
4. rerun post-rollback verification checklist.

---

## Related docs
- Install/bootstrap: [`install-and-bootstrap.md`](./install-and-bootstrap.md)
- Recovery/rollback: [`recovery-and-rollback.md`](./recovery-and-rollback.md)
- Troubleshooting matrix: [`troubleshooting-matrix.md`](./troubleshooting-matrix.md)
- Runtime internals: [`../../architecture/runtime-lifecycle.md`](../../architecture/runtime-lifecycle.md)
