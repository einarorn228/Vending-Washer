# Reisa Phase 10 Execution Note

## Files changed
- `backend/app.py`
- `backend/flask_server.py`
- `backend/services/reisa_audit_service.py`
- `backend/services/reisa_diagnostics_service.py`
- `backend/services/reisa_failure_taxonomy.py` (new)
- `backend/services/reisa_replay_service.py`
- `backend/services/reisa_retry_service.py`
- `backend/setup/seed_settings.py`
- `backend/tests/test_reisa_hardening.py`
- `docs/reisa_phase10_execution_note.md` (new)

## Observability/correlation improvements added
- Added normalized Reisa failure categorization (`reisa_failure_taxonomy`) to classify failures while preserving raw error details (`error_message`, status code) in durable logs.
- Extended audit and retry diagnostics payloads to include `failure_category`.
- Added explicit correlation metadata between audit and retry layers using payload-level correlation keys:
  - `source_audit_log_id` on retry jobs created from retryable audit failures.
  - `resolved_by_audit_log_id` on retry jobs after successful replay.
- `record_reisa_audit(...)` now returns audit log ID so replay paths and retry creation can persist explicit linkage.

## Operator/admin diagnostics added or improved
- Added richer service-level diagnostics method:
  - `get_reisa_session_diagnostics(session_uid, limit)`
  - returns session summary, related audit events, related retry jobs, recovery state counters, and likely next operator action.
- Added admin endpoints (existing endpoints preserved):
  - `GET /admin/reisa/session/<session_uid>`
  - `GET /admin/reisa/audit/<session_uid>`
- Enhanced retry jobs diagnostics output with:
  - normalized `failure_category`
  - `correlation` object (`source_audit_log_id`, `resolved_by_audit_log_id` when present)

## Optional worker/automation
- Added optional safe auto-retry worker loop (`run_retry_worker_loop`) with settings guard.
- Worker behavior:
  - disabled by default
  - only processes due jobs
  - bounded by configurable batch size
  - runs at configurable interval
- Seeded safe defaults:
  - `reisa_retry_worker_enabled = false`
  - `reisa_retry_worker_interval_sec = 30`
  - `reisa_retry_worker_batch_size = 20`
- Worker is started as a daemon thread in `app.py`, but it remains inactive unless explicitly enabled in settings.

## Behavior that remains unchanged
- Existing local provider mode behavior is unchanged.
- Existing manual replay endpoints and flows remain available and compatible.
- Existing retry/replay semantics remain action-scoped and idempotency-guarded.
- Existing admin endpoints are preserved.
- Raw error messages and redacted request/response payload storage behavior is preserved.

## Remaining risks
- Correlation metadata is stored in redacted request payload JSON on retry jobs to avoid schema migration; this is explicit and practical but not as strongly typed as dedicated DB columns.
- Existing older retry rows (created before Phase 10) may not have correlation metadata.
- Classification taxonomy is heuristic and may need tuning for site-specific provider error messages.
- Optional worker has no distributed lock; in multi-process deployments, workers should be enabled carefully (single active process recommended).

## Recommended next phase
- Add explicit schema-level typed correlation columns and lightweight migration support (`source_audit_log_id`, `resolved_by_audit_log_id`) once migration policy is approved.
- Add operator-facing replay provenance and timeline endpoint joining session, audit, and retry history chronologically.
- Add bounded alerting hooks (e.g., exhausted retry job counters) for proactive ops monitoring.
