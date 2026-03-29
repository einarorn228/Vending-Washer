# Recovery and Rollback Runbook

## Purpose
Use this runbook when a deployment/update leaves the kiosk system unhealthy and you need to restore service safely.

This document covers:
- failure scenarios,
- when rollback is appropriate,
- safe shutdown/restart,
- DB/config preservation,
- post-rollback verification,
- branch handling for mixed-failure states.

---

## Common failure scenarios
1. Backend process does not start (import/runtime exception).
2. Backend starts, but scanner/telemetry/background behavior is unhealthy.
3. Frontend works visually, but machine starts fail.
4. Auth/admin access broken (API key or admin credentials mismatch).
5. Reisa sync/retry/replay failures accumulate.
6. Hardware goes offline after code update/config drift.

---

## When rollback is appropriate
Rollback is appropriate when:
- service is materially degraded and no fast fix is available,
- update introduced unknown behavior and operator confidence is low,
- correctness of start/usage accounting is uncertain,
- recovery attempts exceed acceptable downtime.

Do **not** keep hot-fixing blindly while in unstable state if you can quickly restore known-good commit.

---

## Safety-first shutdown and preservation

### 1) Stop frontend and backend
Terminate terminals/services running:
- `python -m backend.app`
- `npm run dev` (or kiosk launcher)

### 2) Preserve current DB and logs before changes
```bash
cp codes.db "codes.db.failure-snapshot.$(date +%Y%m%d-%H%M%S).bak"
cp -r backend/logs "backend/logs.failure-snapshot.$(date +%Y%m%d-%H%M%S)"
```

### 3) Record current commit and branch
```bash
git rev-parse --short HEAD
git branch --show-current
```

---

## Rollback workflow

### A. Return to last known-good commit
```bash
git log --oneline -n 20
# identify known-good SHA
git checkout <KNOWN_GOOD_SHA>
```

If using branch-based deployments, reset branch according to your change-management process.

### B. Reinstall dependencies at rolled-back revision
```bash
# backend
source .venv/bin/activate  # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# frontend
cd frontend
npm install
cd ..
```

### C. Decide DB strategy
- If DB schema/data is suspected healthy: keep current `codes.db`.
- If schema/data is suspected corrupted by failed update:
  1. move broken DB aside,
  2. restore pre-update backup.

Example:
```bash
mv codes.db codes.db.failed.$(date +%Y%m%d-%H%M%S)
cp codes.db.preupdate.<timestamp>.bak codes.db
```

### D. Re-run bootstrap scripts
```bash
python -m backend.setup.seed_settings
python -m backend.setup.seed_machines
```

### E. Start services
```bash
python -m backend.app
```
Then:
```bash
cd frontend
npm run dev
```

---

## Post-rollback verification checklist
1. `curl /api/ui_state` returns valid JSON.
2. Admin endpoint with API key + Basic auth works.
3. Generate code endpoint works.
4. Machine snapshot appears in UI state.
5. Logs show telemetry loop active (if hardware expected).
6. If Reisa enabled, diagnostics endpoints return and no unexpected explosion of pending jobs.

Reference commands:
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/codes
```

---

## Branch: backend starts but system is unhealthy

Symptoms:
- API routes respond, but machine starts fail,
- UI stuck in `machine_starting`/error loops,
- telemetry state stale/offline.

Next actions:
1. Check backend logs (`backend/logs/app.log`, `events.log`, `errors.log`).
2. Validate machine/device definitions in DB.
3. Confirm `backend_relay_enabled` and relevant thresholds/timeouts.
4. Run targeted checks from troubleshooting matrix before deciding second rollback.

---

## Branch: frontend works but hardware/integration is broken

Symptoms:
- UI loads and state polls,
- scanner/i4/Shelly/telemetry/Reisa actions fail.

Next actions:
1. Verify hardware network/serial connectivity first.
2. Validate device IPs and machine config rows.
3. Test scanner with `python tools/test_scanner.py`.
4. Check Reisa diagnostics (`/admin/reisa/sync_failures`, `/admin/reisa/retry_jobs`).
5. If breakage aligned exactly with update and no quick fix is clear, rollback code while preserving DB snapshot.

---

## What to avoid during incident response
- Don’t delete `codes.db` unless you intentionally accept full local state reset.
- Don’t toggle many settings simultaneously without recording original values.
- Don’t run replay/retry actions repeatedly without checking idempotency and job status.
- Don’t assume frontend success means machine-control path is healthy.

---

## Related docs
- Update flow: [`update-and-upgrade.md`](./update-and-upgrade.md)
- Troubleshooting matrix: [`troubleshooting-matrix.md`](./troubleshooting-matrix.md)
- Reisa operator playbook: [`../../integrations/reisa/runbooks/reisa-operator-playbook.md`](../../integrations/reisa/runbooks/reisa-operator-playbook.md)
