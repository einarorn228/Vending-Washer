# Maintenance Tasks Runbook

This runbook is for recurring operational hygiene.

Source of truth:
- startup/bootstrap: `backend/app.py`, `backend/flask_server.py`, `backend/setup/*`
- settings model: `backend/models/setting_model.py`
- diagnostics services: `backend/services/reisa_*`

## Pre-change checklist (every maintenance window)
1. Record current commit.
2. Backup DB and logs.
3. Confirm `/api/ui_state` is healthy before changing anything.
4. Confirm API key/admin credentials are available.

Commands:
```bash
git rev-parse --short HEAD
cp codes.db "codes.db.pre-maint.$(date +%Y%m%d-%H%M%S).bak"
cp -r backend/logs "backend/logs.pre-maint.$(date +%Y%m%d-%H%M%S)"
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
```

## Weekly tasks

## 1) Verify auth and core routes
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/codes
```

## 2) Check recent errors
```bash
tail -n 200 backend/logs/errors.log
```

## 3) Check Reisa failure queue (if Reisa enabled)
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/reisa/sync_failures
```

## 4) Validate machine availability snapshot
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
```

## Monthly tasks

## 1) Credential hygiene
- rotate admin password hash on schedule.
- rotate API key according to site policy.

## 2) Settings drift review
```bash
sqlite3 codes.db "SELECT key,value FROM settings ORDER BY key;"
```

Review specifically:
- provider settings
- timeout settings (`button_select_timeout_sec`, `machine_reservation_minutes`)
- scanner settings
- `backend_relay_enabled`

## 3) Dependency refresh + smoke test in controlled window
```bash
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
python -m unittest discover backend/tests
```

## 4) Hardware mapping audit
```bash
sqlite3 codes.db "SELECT id,name,role,ip,relay_channel,input_channel,metric_source FROM devices ORDER BY id;"
sqlite3 codes.db "SELECT id,name,ui_name,uni_device_id,i4_device_id,i4_button_index,is_enabled FROM machines ORDER BY id;"
```

## Post-change verification checklist
1. backend process restarts cleanly.
2. `/api/ui_state` returns valid payload.
3. one scan/start test works.
4. no new recurring exceptions in `errors.log`.
5. if Reisa enabled, no unexpected growth in pending/exhausted jobs.

## High-risk operations
- Deleting `codes.db` during routine maintenance (full local state reset).
- Running bulk replay actions without first inspecting session diagnostics.
- Assuming seed scripts reconcile existing data drift.

## Required warning
Seed scripts are not migrations. Re-running them does not normalize all existing rows.

## Unknown / requires verification from code
- No automated maintenance scheduler exists beyond runtime cleanup of expired codes.
