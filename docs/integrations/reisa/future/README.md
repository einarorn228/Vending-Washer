# Reisa Future Ideas and Backlog

This backlog captures work that is **not yet done** and organizes it by priority.

## 1) Important next things to test/validate (highest priority)

### A. End-to-end validation priorities
- Validate full Reisa-mode lifecycle in staging with realistic failure injection:
  - scan/authorize/start-confirmed commit/completion
  - transient network failures and recovery via replay/retry
- Validate provider-setting stability during active sessions (ensure session-bound routing remains consistent under config changes).
- Validate completion correlation under telemetry edge cases (rapid stop/start, delayed/out-of-order callbacks).

### B. Must-test operational recovery paths
- Exercise replay behavior for each action (`start_status`, `deduct`, `completion_status`) across retryable vs non-retryable failures.
- Verify optional retry worker behavior when enabled:
  - due-job pickup, bounded batch behavior, and no duplicate processing surprises.
- Confirm diagnostics endpoints are sufficient for operator triage of failed/exhausted jobs.

## 2) Good ideas for later (important, but not immediate blockers)

### A. Observability improvements
- Add session timeline view that joins usage session + audit + retry events chronologically.
- Add bounded alerting hooks for exhausted retries / repeated failure categories.
- Improve diagnostics payload consistency for quicker incident review.

### B. Schema hardening ideas
- Promote correlation metadata (`source_audit_log_id`, `resolved_by_audit_log_id`) from JSON payload blobs into typed DB columns.
- Add migration-safe schema evolution plan for retry/audit correlation fields.
- Consider stronger completion correlation keys beyond “latest eligible session per machine”.

### C. Deployment hardening ideas
- Add a clear single-worker ownership strategy (or lock) before using retry worker in multi-process deployments.
- Document environment-specific retry-worker rollout procedures and safe defaults.

## 3) Nice-to-have / non-essential improvements

### A. Operator UX improvements
- Add operator-friendly replay provenance UI/endpoint views (what failed, what replayed, what succeeded, when).
- Add compact “likely next action” hints for common failure categories.

### B. Optional architecture cleanup
- Reduce remaining mixed DB session usage patterns.
- Consolidate duplicate startup side effects where still present.
- Continue trimming legacy compatibility paths once no longer needed.

## Backlog curation rules
- Keep this file focused on actionable items.
- Move an item to completed only after implementation and an execution note are added under `../completed/phases/`.
- Avoid adding speculative ideas without a clear operator or reliability benefit.
