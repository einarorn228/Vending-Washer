# Reisa Phase 9.1 Execution Note

## Files changed
- `backend/services/reisa_replay_service.py`
- `backend/services/usage_session_service.py`
- `backend/tests/test_reisa_hardening.py`
- `docs/reisa_phase9_1_execution_note.md` (new)

## Replay consistency gaps fixed
- Fixed gap where `start_status` replay could succeed while leaving `deduct` unsynced.
- Fixed gap where successful `deduct` replay did not repair local usage-session commit state.
- Fixed gap where successful `completion_status` replay could leave stale `completion_sync_failed` markers.

## How session repair now works after replay success
- Added small usage-session repair helpers:
  - `mark_commit_recovered(...)`
  - `mark_completion_recovered(...)`
  - `clear_external_sync_error(...)` (utility for explicit stale-marker clearing)
- `deduct` replay success now repairs local session to `commit_ok`, sets `committed_quantity`, updates `remaining_after_commit` when available, and clears stale commit failure markers.
- `completion_status` replay success now keeps completion idempotent while clearing stale completion-sync failure markers.
- `start_status` replay now checks whether deduct is still missing and attempts deduct immediately in replay flow; if deduct fails retryably, normal retry-job creation path remains in effect so session is not silently left half-synced.

## Behavior remains unchanged
- Retry/replay remains action-specific and idempotent.
- Local mode behavior remains unchanged.
- Admin retry endpoints and diagnostics route shapes remain unchanged.
- No architecture redesign or unrelated feature work was introduced.

## Remaining risks
- Deduct replay still assumes quantity `1`, aligned with current commit lifecycle design.
- If start-status replay succeeds but deduct replay fails with non-retryable external rejection, operator intervention is still required.
- Existing session correlation assumptions from earlier phases remain unchanged.

## Consistency/readiness assessment
- Yes: the retry/replay implementation is now materially more consistent for Phase 9 scope because successful replay repairs both external sync and local usage-session lifecycle markers.
- This is sufficient to proceed to the next incremental hardening phase.
