# Reisa Phase 9 Execution Note

## Files changed
- `backend/models/__init__.py`
- `backend/models/reisa_retry_job_model.py` (new)
- `backend/providers/reisa_provider.py`
- `backend/services/reisa_audit_service.py`
- `backend/services/reisa_diagnostics_service.py`
- `backend/services/reisa_retry_service.py` (new)
- `backend/services/reisa_replay_service.py` (new)
- `backend/flask_server.py`
- `backend/tests/test_reisa_hardening.py`
- `docs/reisa_phase9_execution_note.md` (new)

## Retry job model introduced
- Added durable table/model `reisa_retry_jobs` via `ReisaRetryJob`.
- Retry jobs are action-scoped (`start_status`, `deduct`, `completion_status`) and session-bound (`session_uid`).
- Each job tracks bounded scheduling and outcomes:
  - `retry_count`
  - `max_retries`
  - `next_attempt_at`
  - `status` (`pending`, `retrying`, `succeeded`, `exhausted`, `skipped`)
  - `last_error` / `last_status_code`

## How retry jobs are created
- Retry jobs are created from durable Reisa audit failures only when all are true:
  - audit `result == error`
  - audit `retryable == true`
  - action is one of `start_status`, `deduct`, `completion_status`
  - `session_uid` is present
- This keeps retries focused on external/transient failures (timeouts/network/5xx surfaced as retryable by existing client/service logic).
- Existing non-retryable contract/config failures are retained in audit diagnostics but are not blindly queued.

## Replay safety/idempotency enforcement
- Replay operates per failed external action, not per whole session.
- Before replaying, service checks durable local state + audit history to skip already-succeeded actions:
  - skip `start_status` replay if a successful start-status audit exists.
  - skip `deduct` replay if deduct already succeeded or local session is already committed.
  - skip `completion_status` replay if completion-status already succeeded.
- Replay reconstructs provider session context from persisted `UsageSession` and provider reference data.
- Replay remains session/provider-consistent by resolving and using Reisa provider path only for Reisa sessions.

## Admin/debug tools added
- Added admin-protected endpoints:
  - `GET /admin/reisa/retry_jobs`
  - `POST /admin/reisa/retry/<job_id>`
  - `POST /admin/reisa/retry_due`
- Existing diagnostics now also include retry-job snapshots for easier operations correlation.

## Behavior that should remain unchanged
- Local provider mode behavior is unchanged.
- Core local lifecycle (scan/start/telemetry-confirmed start UI transitions) remains unchanged.
- Existing `/admin/reisa/sync_failures` diagnostics remain available.
- No architecture rewrite, no large async framework, no frontend behavior redesign.

## Remaining risks
- Replay currently assumes quantity `1` for deduct replays (aligned with current commit flow).
- Completion replay marks local completion after successful external completion replay; if local completion was already set by prior path, idempotent skip guards handle it but telemetry edge-cases still depend on existing completion correlation strategy.
- Automatic replay exists as optional manual-triggered due-job endpoint, not a dedicated background scheduler.

## Recommended next phase
- Add stronger operator tooling around replay correlation and root-cause triage:
  - audit-event-to-job linkage identifiers
  - richer retry reason taxonomy
  - optional periodic safe due-job worker with explicit feature flag
