# Auth and Admin Access Runbook

Code source of truth:
- `backend/controllers/ui_api.py`
- `backend/flask_server.py`
- `backend/setup/seed_settings.py`
- `backend/scripts/get_api_key.py`

## Auth model summary
- `/generate_code` requires `X-API-KEY`.
- `/api/*` routes currently accept API key from either:
  - `X-API-KEY` header, or
  - `api_key` query parameter.
- Admin routes require both `X-API-KEY` and HTTP Basic auth.
- Basic auth password is checked by SHA-256 hash against `settings.admin_password_hash`.

## Security warning: query-string API keys
- Query-string API keys are supported by current `/api/*` code path for compatibility.
- They are leak-prone (browser history, reverse-proxy/access logs, shared URLs, and screenshots).
- Operational guidance: use `X-API-KEY` header only.

## Safe operation: retrieve current API key
```bash
python backend/scripts/get_api_key.py
```

Use with request:
```bash
curl -H "X-API-KEY: <KEY>" http://127.0.0.1:5000/api/ui_state
```

## Initial bootstrap defaults
From `seed_settings.py` defaults:
- `admin_username=admin`
- `admin_password_hash=sha256("admin")`
- `api_key` generated on first run if missing

High-risk note:
- Default admin credentials must be rotated immediately.

## Rotate API key

## Step 1: write new key
```bash
python - <<'PY'
import secrets
from backend.models import Session
from backend.models.setting_model import update_setting_value
s = Session()
try:
    key = secrets.token_hex(32)
    update_setting_value(s, 'api_key', key)
    print(key)
finally:
    s.close()
PY
```

## Step 2: update clients
- frontend localStorage `API_KEY` or `frontend/.env` `VITE_API_KEY`
- automation and curl scripts

## Step 3: verify
```bash
NEW_KEY="<paste_new_key>"
curl -H "X-API-KEY: $NEW_KEY" http://127.0.0.1:5000/api/ui_state
```
Expected: HTTP 200 with state payload.

## Rotate admin password hash

Generate SHA-256 hash for new plaintext password:
```bash
python - <<'PY'
import hashlib
pw = 'ChangeMeStrong'
print(hashlib.sha256(pw.encode('utf-8')).hexdigest())
PY
```

Apply hash:
```bash
python - <<'PY'
from backend.models import Session
from backend.models.setting_model import update_setting_value
s = Session()
try:
    update_setting_value(s, 'admin_password_hash', '<hash_from_previous_step>')
finally:
    s.close()
PY
```

Optional username rotation:
```bash
python - <<'PY'
from backend.models import Session
from backend.models.setting_model import update_setting_value
s = Session()
try:
    update_setting_value(s, 'admin_username', 'ops_admin')
finally:
    s.close()
PY
```

Verify admin auth:
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -u ops_admin:ChangeMeStrong -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/codes
```

## Common auth failures

## API key failure
Response:
```json
{"success":false,"message":"Invalid API key"}
```
or
```json
{"error":"Invalid or missing API key"}
```

Likely causes:
- stale client key
- missing header
- rotated key not distributed

## Admin Basic auth failure
Response:
```json
{"error":"Admin authentication required"}
```

Likely causes:
- missing Basic header
- plaintext password does not match stored hash
- wrong username

## Lockout recovery

Precondition:
```bash
cp codes.db "codes.db.pre-auth-recovery.$(date +%Y%m%d-%H%M%S).bak"
```

Recovery steps:
1. Set known API key and admin hash directly in DB via Python helper scripts shown above.
2. Verify `/api/ui_state` with new key.
3. Verify one `/admin/*` route with new Basic credentials.
4. Record new credentials in secure credential store.

## Requires restart
- No restart required for key/hash changes; values are read at request time.

## High-risk operations
- Changing both API key and admin credentials at once without staged verification can lock out all operators.
- Writing malformed hashes can permanently block Basic auth until manually repaired.

## Unknown / requires verification from code
- No dedicated account lockout/rate limiting logic is implemented for repeated failed admin attempts.
