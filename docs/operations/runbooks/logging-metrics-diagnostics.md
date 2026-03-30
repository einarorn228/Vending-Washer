# Logging, Metrics, and Diagnostics Runbook

Source of truth:
- logger configuration: `backend/utils/logger.py`
- metrics storage: `backend/metrics.py`
- metrics endpoints: `backend/flask_server.py`

## Log files
Created under `backend/logs/`:
- `app.log` (general runtime + HTTP request logs)
- `events.log` (structured event flow)
- `errors.log` (error-focused log stream)

Rotation settings in code:
- max size: 10 MB
- backups: 5

## Request logging behavior
- Successful `/api/ui_state` poll requests are heavily filtered/sampled.
- Slow requests (>300ms) are force-logged.
- Error responses are logged.

Operational implication:
- Do not assume every poll call is present in logs.

## Event names you will see
Common event stream markers:
- `SCAN received`
- `START_REQUESTED`
- `START_CONFIRMED`
- `RUNSTATE_STARTED`
- `RUNSTATE_STOPPED`
- `BUTTON_BOX_ON` / `BUTTON_BOX_OFF`
- `SELECTION_TIMEOUT`
- `DEVICE_OFFLINE`
- `TELEMETRY_READ`

## Basic diagnostic commands

Tail logs:
```bash
tail -f backend/logs/app.log
```

```bash
tail -f backend/logs/events.log
```

```bash
tail -f backend/logs/errors.log
```

Search for machine-specific events:
```bash
rg "washer1|START_|RUNSTATE_|DEVICE_OFFLINE" backend/logs/events.log
```

## Log level control
Priority order in code:
1. `LOG_LEVEL` environment variable
2. `settings.log_level`
3. fallback `INFO`

Set for current shell:
```bash
export LOG_LEVEL=DEBUG
python -m backend.app
```

Requires restart:
- Yes, logger config is established at process startup.

## Metrics endpoints
All admin-protected (API key + Basic auth).

## `GET /admin/metrics`
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/metrics
```

## `GET /admin/metrics/export.csv`
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -u admin:<password> -H "X-API-KEY: $API_KEY" \
  http://127.0.0.1:5000/admin/metrics/export.csv -o metrics_export.csv
```

## Useful metrics to watch
- `http_requests_total`
- `http_request_duration_ms`
- `machine_start_attempts`
- `machine_start_failures`
- `machines_started_total`
- `scan_total`
- `scan_to_start_ms`
- `machine_available` (gauge by machine)
- `shelly_request_ms`, `shelly_rtt_ms`
- derived gauge: `code_fail_rate`

## Incident workflow using logs + metrics
1. Confirm auth and basic health (`/api/ui_state`).
2. Check `errors.log` for recent exceptions.
3. Correlate with `events.log` sequence for the affected machine/session.
4. Pull `/admin/metrics` snapshot and inspect start failure counters and request latency.
5. If Reisa involved, inspect `/admin/reisa/sync_failures`.

## High-risk pitfalls
- Interpreting missing poll logs as backend outage (poll filtering/sampling is intentional).
- Changing log level in DB and expecting immediate effect without restart.

## Unknown / requires verification from code
- No external metrics backend exporter exists; metrics are in-process and reset on process restart.
