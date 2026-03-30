# Database Schema and Lifecycle

Source of truth:
- `backend/models/*.py`
- lifecycle services in `backend/services/*`
- bootstrap scripts in `backend/setup/*`

DB engine: SQLite file `codes.db` in repository root (`sqlite:///codes.db`).

## High-risk reality
- Seed scripts are not migrations.
- Existing rows are mostly untouched by seed scripts.
- Bootstrap fills missing defaults; it does not reconcile all drift.

## Tables

## `settings`
Model: `backend/models/setting_model.py`

Columns:
- `id` INTEGER PK
- `key` STRING UNIQUE NOT NULL
- `value` STRING NOT NULL

Used for auth, provider mode, timeouts, scanner config, and feature toggles.

## `codes`
Model: `backend/models/code_model.py`

Columns:
- `code` STRING PK
- `order_id` STRING
- `usage_limit` INTEGER
- `current_usage` INTEGER
- `expiration_date` DATETIME nullable
- `created_at` DATETIME

Lifecycle:
- created by `POST /generate_code`
- usage incremented by local provider commit
- may be deleted by cleanup if expired

## `scan_logs`
Model: `backend/models/scan_log_model.py`

Columns:
- `id` INTEGER PK
- `code` STRING
- `order_id` STRING
- `timestamp` DATETIME
- `result` STRING
- `details` STRING

Writes occur during scan ingestion (valid and invalid attempts).

## `devices`
Model: `backend/models/device_model.py`

Columns:
- `id` INTEGER PK
- `name` STRING
- `role` STRING
- `model` STRING
- `ip` STRING
- `relay_channel` INTEGER nullable
- `input_channel` INTEGER nullable
- `metric_source` STRING nullable
- `created_at` DATETIME
- `updated_at` DATETIME

`role` values drive behavior (`button_box`, `i4`, `washer_uni`, etc.).

## `machines`
Model: `backend/models/machine_model.py`

Columns:
- `id` INTEGER PK
- `name` STRING (slug used by backend)
- `ui_name` STRING (display label)
- `uni_device_id` FK -> devices.id
- `uni_relay_channel` INTEGER
- `i4_device_id` FK -> devices.id nullable
- `i4_button_index` INTEGER nullable
- `is_enabled` INTEGER

## `machine_configs`
Model: `backend/models/machine_model.py` (`MachineConfig`)

Columns:
- `machine_id` PK + FK -> machines.id
- `on_threshold` INTEGER
- `off_threshold` INTEGER
- `on_confirm_ms` INTEGER
- `off_confirm_ms` INTEGER
- `poll_interval_ms` INTEGER

Used by telemetry debounce and run-state transitions.

## `usage_sessions`
Model: `backend/models/usage_session_model.py`

Columns include:
- identity: `session_uid` unique, `provider`, `provider_reference`
- request context: `identifier_type`, `identifier_value_masked`, `machine_id`, `scan_source`
- lifecycle: `state`, `requested_quantity`, `committed_quantity`, `remaining_after_commit`
- failure: `error_code`, `error_detail`
- timing: `created_at`, `updated_at`, `started_at`, `completed_at`

Primary lifecycle table for scan/start/commit/completion durability.

## `reisa_audit_logs`
Model: `backend/models/reisa_audit_model.py`

Columns:
- `id` INTEGER PK
- `session_uid` indexed
- request metadata: `request_type`, `endpoint`, `method`, `provider_reference`
- payload fields: redacted request/response payloads
- outcome fields: `response_status_code`, `result`, `retryable`, `error_message`
- `created_at`

Retryable error rows can trigger retry-job creation.

## `reisa_retry_jobs`
Model: `backend/models/reisa_retry_job_model.py`

Columns:
- identity/context: `id`, `session_uid`, `provider`, `action_type`, `provider_reference`
- status control: `status`, `retry_count`, `max_retries`, `next_attempt_at`, `disabled`
- diagnostics: `last_error`, `last_status_code`, `last_attempt_at`, `resolved_at`
- timestamps: `created_at`, `updated_at`

Statuses used in code:
- `pending`
- `retrying` (listed as a valid status filter state)
- `succeeded`
- `exhausted`
- `skipped`

## Relationship map

Logical (not all enforced by DB FK):
- `machines.uni_device_id` -> `devices.id`
- `machines.i4_device_id` -> `devices.id`
- `machine_configs.machine_id` -> `machines.id`
- `scan_logs.code` refers to `codes.code` by convention
- `usage_sessions.session_uid` links to `reisa_audit_logs.session_uid` and `reisa_retry_jobs.session_uid`

## Lifecycle flows

## Local provider flow
1. Scan accepted -> `scan_logs` insert.
2. Usage session created (`state=scanned`).
3. Start requested -> `state=start_requested`.
4. Telemetry confirms start -> local commit increments `codes.current_usage`.
5. `usage_sessions` marked `commit_ok` then completion marks `completed` when run stops.

## Reisa provider flow
1. Scan accepted -> session created with provider `reisa`.
2. Start requested and telemetry confirms start.
3. Commit performs Reisa start status + deduct.
4. Failures are audited in `reisa_audit_logs`.
5. Retryable failures create/refresh `reisa_retry_jobs`.
6. Replay can repair `usage_sessions` state and clear external sync errors.

## Idempotency behavior

Implemented safeguards:
- `mark_committed` ignores duplicate commit transitions when already committed/completed.
- `mark_completed_for_session` and machine completion helpers ignore duplicate completion.
- replay logic checks successful prior audit actions and may mark jobs `skipped`.

Unknown / requires verification from code:
- Whether any external caller sets job status to `retrying` today. The status is recognized but replay code primarily toggles between pending/succeeded/exhausted/skipped.

## Bootstrap behavior: what it does and does not do

## `backend.setup.seed_settings`
Does:
- inserts missing keys from `DEFAULT_SETTINGS`
- ensures `log_level` and generated `api_key` if absent

Does not:
- overwrite existing setting values
- enforce schema migrations

## `backend.setup.seed_machines`
Does:
- seed `devices` only when `devices` table is empty
- seed `machines` and `machine_configs` only when `machines` table is empty

Does not:
- update existing machine/device rows when defaults change
- reconcile partial drift in populated tables

## Backup and inspection commands

## Backup before risky changes
```bash
cp codes.db "codes.db.backup.$(date +%Y%m%d-%H%M%S)"
```

## Quick table inspection
```bash
sqlite3 codes.db '.tables'
sqlite3 codes.db 'SELECT key,value FROM settings ORDER BY key;'
sqlite3 codes.db 'SELECT session_uid,provider,state,error_code,updated_at FROM usage_sessions ORDER BY updated_at DESC LIMIT 20;'
sqlite3 codes.db 'SELECT id,session_uid,request_type,result,retryable,created_at FROM reisa_audit_logs ORDER BY id DESC LIMIT 20;'
sqlite3 codes.db 'SELECT id,session_uid,action_type,status,retry_count,next_attempt_at FROM reisa_retry_jobs ORDER BY id DESC LIMIT 20;'
```

## Verify model registration coverage
```bash
python - <<'PY'
from backend.models import Base
print(sorted(Base.metadata.tables.keys()))
PY
```

Expected table names include:
`codes, devices, machine_configs, machines, reisa_audit_logs, reisa_retry_jobs, scan_logs, settings, usage_sessions`.
