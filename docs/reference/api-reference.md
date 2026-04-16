# API Reference

This document is the HTTP contract for the current backend implementation.

Code source of truth:
- `backend/flask_server.py`
- `backend/controllers/ui_api.py`

## Runtime base URL
- Default backend bind: `http://127.0.0.1:5000`

## Authentication modes

### API key only
`/generate_code` requires API key in header:

```http
X-API-KEY: <api_key_from_settings>
```

For `ui_api` routes (`/api/*`), current code accepts either:
- `X-API-KEY` header, or
- `api_key` query parameter.

**Security warning:** query-string API keys are discouraged for operational use. They are leak-prone in browser history, logs, proxies, and shared URLs. Use `X-API-KEY` header in production/operator workflows.

### API key + Basic auth
All `/admin/*` routes require both:
- `X-API-KEY`
- `Authorization: Basic base64(username:password)`

Password verification uses SHA-256 hash comparison against `settings.admin_password_hash`.

## Common auth failure responses

### Missing/invalid API key
```json
{"error":"Invalid or missing API key"}
```
Status: `401`

### Missing/invalid admin Basic auth
```json
{"error":"Admin authentication required"}
```
Status: `401`
Also includes `WWW-Authenticate: Basic realm="Admin Area"`.

---

## Public and UI routes

## `POST /generate_code`
Auth: API key in `X-API-KEY` header.

Purpose: create a new local code row.

Request body:
```json
{"order_id":"ORDER-123","usage_limit":1}
```

Success response (201):
```json
{
  "message":"QR code generated successfully.",
  "code":"Ab12Cd34",
  "order_id":"ORDER-123",
  "usage_info":{"usage_limit":1,"current_usage":0},
  "status_code":201,
  "expiration_date":null,
  "expiration_message":"Code does not expire while unused."
}
```

Failure examples:
- Missing fields (`400`):
```json
{"error":"Missing order_id or usage_limit"}
```
- Duplicate order_id (`400`):
```json
{
  "error":"Order ID already exists",
  "code":"EXISTING1",
  "usage_limit":1,
  "current_usage":0,
  "status_code":400
}
```

Auth failure (`401`):
```json
{"error":"Invalid or missing API key"}
```

Notes:
- `usage_limit` is not validated for range/type beyond JSON parsing; callers must send sane integers.
- Expiration comes from setting `code_expiration_days` if configured.

---

## `POST /api/scan_code`
Auth: API key (`X-API-KEY` header recommended; `api_key` query parameter also accepted by current code).

Purpose: ingest a scan event and arm a code for machine selection.

Request body:
```json
{"code":"Ab12Cd34"}
```

Success response (`200`):
```json
{
  "success":true,
  "uses_left":1,
  "machines":[{"id":"washer1","name":"Washer 1","available":true}],
  "message":"Select a machine using the physical buttons"
}
```

Failure responses:
- Busy state (`409`):
```json
{"success":false,"message":"System busy. Please wait."}
```
- Invalid or missing code (`400`):
```json
{"success":false,"message":"Code expired or invalid."}
```
or
```json
{"success":false,"message":"Missing code"}
```

Auth failure (`401`):
```json
{"success":false,"message":"Invalid API key"}
```

Notes:
- Writes `scan_logs` for accepted/rejected scans.
- In Reisa mode, lookup/authorize behavior depends on provider settings.

---

## `POST /api/start_machine`
Auth: API key (`X-API-KEY` header recommended; `api_key` query parameter also accepted by current code).

Purpose: request start for a machine with explicit `code` + `machine_id`.

Request body:
```json
{"code":"Ab12Cd34","machine_id":"washer1"}
```

Success (`200`):
```json
{"success":true,"uses_left":1,"message":"Washer 1 is powered on. Select a program on the machine (max 10 minutes)."}
```

Failure responses:
- Missing data (`400`):
```json
{"success":false,"message":"Missing data"}
```
- Flow conflict/rejection (`409`):
```json
{"success":false,"message":"Machine not available."}
```
or provider message.

Auth failure (`401`):
```json
{"success":false,"message":"Invalid API key"}
```

Notes:
- Start request may succeed before telemetry confirms machine run.
- Usage commit happens on telemetry-confirmed start, not at button press/start request time.

---

## `POST /api/touch_select_machine`
Auth: API key (`X-API-KEY` header recommended; `api_key` query parameter also accepted by current code).

Purpose: request machine selection/start in touch mode using backend-held armed scan context (no raw `code` in request).

Request body:
```json
{"machine_id":"washer1"}
```

Success (`200`):
```json
{
  "success":true,
  "message":"Washer 1 is powered on. Select a program on the machine (max 10 minutes).",
  "uses_left":1,
  "state":"machine_starting"
}
```

Failure responses:
- Missing `machine_id` (`400`):
```json
{"success":false,"message":"Missing machine_id"}
```
- Invalid `machine_id` (`400`):
```json
{"success":false,"message":"Invalid machine_id"}
```
- Touch mode disabled (`409`):
```json
{"success":false,"message":"Touch selection is disabled."}
```
- Wrong UI state (must be `choose_machine`) (`409`):
```json
{"success":false,"message":"Machine selection is not active.","state":"waiting_for_code"}
```
- No armed/pending scan or start conflict (`409`):
```json
{"success":false,"message":"No valid scan in progress.","uses_left":null,"state":"choose_machine"}
```
or
```json
{"success":false,"message":"Machine not available.","uses_left":null,"state":"choose_machine"}
```

Preconditions:
- `kiosk_input_mode` resolves to `touch`.
- Current backend UI state is `choose_machine`.
- Backend has an armed, valid scan/session context.
- Target machine exists and can be started.

Notes:
- This endpoint is additive and does not replace `/api/i4_event`.
- Hardware-button flow remains unchanged.

---

## `POST /api/i4_event` and `GET /api/i4_event?button=<index>`
Auth: API key (`X-API-KEY` header recommended; `api_key` query parameter also accepted by current code).

Purpose: submit physical button index.

POST request body example:
```json
{"button":0}
```

GET example:
```bash
curl -H "X-API-KEY: <KEY>" "http://127.0.0.1:5000/api/i4_event?button=0"
```

Success (`200`):
```json
{"success":true,"message":"...","uses_left":1}
```

Failure responses:
- Missing button (`400`):
```json
{"success":false,"message":"Missing button index"}
```
- Invalid button type (`400`):
```json
{"success":false,"message":"Invalid button index"}
```
- Unknown button/no armed code/etc (`409`):
```json
{"success":false,"message":"Unknown button.","uses_left":null}
```

Auth failure (`401`):
```json
{"success":false,"message":"Invalid API key"}
```

---

## `GET /api/ui_state`
Auth: API key (`X-API-KEY` header recommended; `api_key` query parameter also accepted by current code).

Purpose: frontend polling endpoint.

Success (`200`) example:
```json
{
  "state":"waiting_for_code",
  "message":"Scan your code to start",
  "uses_left":null,
  "current_machine":null,
  "input_mode":"hardware_buttons",
  "machines":[{"id":"washer1","name":"Washer 1","available":true}]
}
```

Auth failure (`401`):
```json
{"success":false,"message":"Invalid API key"}
```

Notes:
- Backend is source of truth for UI state.

---

## Admin routes

All routes below require API key + Basic auth.

## `GET /admin/reisa/retry_jobs`
Query params:
- `limit` default `100`
- `status` optional
- `due_only` boolean-like (`1/true/yes/on`)

Success (`200`):
```json
{"limit":100,"count":1,"jobs":[{"id":12,"status":"pending"}]}
```

---

## `GET /admin/reisa/session/<session_uid>`
Query param: `limit`.

Returns session diagnostics payload from `get_reisa_session_diagnostics`.

---

## `GET /admin/reisa/audit/<session_uid>`
Query param: `limit`.

Success example:
```json
{"session_uid":"...","limit":100,"audit_events":[...],"retry_jobs":[...]}
```

---

## `POST /admin/reisa/retry/<job_id>`
Purpose: replay one retry job.

Success (`200`) example:
```json
{"job_id":15,"success":true,"status":"succeeded","message":"Replay succeeded"}
```

Failure (`500`) example:
```json
{"job_id":15,"success":false,"status":"failed","message":"..."}
```

---

## `POST /admin/reisa/retry_due`
Query param: `limit` default `20`.

Success (`200`) example:
```json
{"processed":3,"succeeded":2,"failed":1,"skipped":0,"limit":20}
```

---

## `GET /admin/reisa/sync_failures`
Query param: `limit`.

Success (`200`) returns:
```json
{
  "failed_sessions":[...],
  "failed_audit_events":[...],
  "retry_jobs":[...],
  "limit":100
}
```

---

## `GET /admin/metrics`
Returns in-process counters/gauges/histograms snapshot.

Success (`200`) example:
```json
{"counters":[...],"gauges":[...],"histograms":[...]}
```

---

## `GET /admin/metrics/export.csv`
Returns CSV download (`text/csv`) with columns:
- `timestamp,type,name,labels,metric,value`

---

## `GET /admin/usage/by_order_id/<order_id>`
Returns scan logs for order.

Success (`200`) example:
```json
[{"id":1,"code":"Ab12Cd34","order_id":"ORDER-123","result":"valid","details":"api"}]
```

Not found (`404`) examples:
```json
{"message":"No scan logs found for order_id 'ORDER-123'. Order ID does not exist."}
```
or
```json
{"message":"Order ID 'ORDER-123' has not been scanned yet."}
```

---

## `GET /admin/usage/by_code/<code>`
Same shape as by order id, filtered by code.

---

## `GET /admin/scan_logs/last/<count>`
Returns last scan logs.

Not found (`404`):
```json
{"message":"No scan logs found."}
```

---

## `GET /admin/codes`
Returns all codes.

Not found (`404`):
```json
{"message":"No codes found."}
```

---

## `GET /admin/codes/last/<count>`
Returns most recent codes.

---

## `GET /admin/codes/by_order_id/<order_id>`
Returns codes by order id.

Not found (`404`) example:
```json
{"message":"No codes found for order_id 'ORDER-123'. Order ID does not exist."}
```

---

## `GET /admin/codes/<code>`
Returns one code.

Not found (`404`):
```json
{"message":"Code 'Ab12Cd34' does not exist."}
```

---

## `DELETE /admin/codes/<code>`
Deletes one code.

Success (`200`):
```json
{"message":"Code 'Ab12Cd34' deleted."}
```

Not found (`404`):
```json
{"message":"Code 'Ab12Cd34' does not exist."}
```

---

## `DELETE /admin/codes/by_order_id/<order_id>`
Deletes all codes for order.

Success (`200`):
```json
{"message":"Deleted 2 code(s) for order_id 'ORDER-123'."}
```

Not found (`404`):
```json
{"message":"No codes found for order_id 'ORDER-123'."}
```

---

## `PUT /admin/settings/cors`
Request body:
```json
{"origins":["http://localhost:3000","http://192.168.1.50"]}
```

Success (`200`):
```json
{"message":"CORS origins updated"}
```

Failure (`400`):
```json
{"error":"Missing origins"}
```

Notes:
- Code updates the DB immediately, but CORS is loaded during Flask app init. Restart backend for predictable effect.

---

## `GET /admin/settings/<key>`
Success (`200`):
```json
{"key":"log_level","value":"INFO"}
```

Not found (`404`):
```json
{"error":"Setting not found"}
```

---

## `PUT /admin/settings/<key>`
Request body:
```json
{"value":"DEBUG"}
```

Success (`200`):
```json
{"message":"Setting updated","key":"log_level","value":"DEBUG"}
```

Failure (`400`):
```json
{"error":"Missing value"}
```

---

## Route inventory check command
Use this to verify docs vs implementation:

```bash
python - <<'PY'
from backend.flask_server import app
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    if rule.endpoint != 'static':
        print(','.join(sorted(rule.methods - {'HEAD','OPTIONS'})).ljust(12), rule.rule)
PY
```

If output differs from this document, update this file before changing runbooks.
