# Reisa Phase 4 Execution Note

## Files changed
- `backend/services/usage_session_service.py`
- `backend/services/start_orchestrator.py`
- `backend/controllers/machine_control.py`
- `docs/reisa_phase4_execution_note.md` (new)

## What lifecycle hardening was added
- Added a practical terminal lifecycle state for usage sessions: `completed`.
- Added guarded transition helpers in `usage_session_service`:
  - `mark_committed(...)` enforces a one-way commit transition and skips duplicate commit attempts for already `commit_ok`/`completed` sessions.
  - `mark_completed_for_machine(...)` marks completion for the latest eligible machine session and skips duplicate completion updates.
- Hardened pending-start concurrency handling in `machine_control` by adding a dedicated lock around `_pending_starts` read/write/pop paths (`start_machine`, `consume_pending_start`, selection-timeout path, and offline checks).

## How completion is now persisted
- Wired telemetry `runstate_stopped` events into machine-control listener `_on_runstate_stopped(...)`.
- `_on_runstate_stopped(...)` delegates to `start_orchestrator.handle_run_completed(machine_id)`.
- Orchestrator completion handler calls `mark_completed_for_machine(machine_id)` so the durable usage-session row now records:
  - `state = completed`
  - `completed_at = utc timestamp`

This keeps completion persistence tied to current runtime/telemetry flow, without changing UI behavior.

## What idempotency protections were introduced
- Commit path now uses `mark_committed(...)` instead of unguarded generic state updates.
  - Duplicate commit attempts against a session already in `commit_ok`/`completed` are ignored safely.
- Completion path now uses `mark_completed_for_machine(...)`.
  - Duplicate runstate-stopped callbacks for the same finished run are ignored once `completed_at` is already set or state is already `completed`.
- Pending-start map operations are now lock-protected to reduce race windows where duplicate callback/timeout/offline handlers could interleave unsafely.

## What still remains risky
- Completion correlation currently chooses the latest eligible session for a machine (`commit_ok`/`start_confirmed`) rather than a strict run-id key, so out-of-order telemetry in edge cases could target the wrong recent session.
- Session continuity across process restarts is still partially in-memory for scan→start correlation.
- Mixed SQLAlchemy session patterns across the codebase remain outside this phase scope.

## Ready for first Reisa read-only phase?
- **Yes, with caveats.**
- The local lifecycle now has a clearer durable sequence through start-confirmed commit and completion persistence, plus safer duplicate-transition handling.
- Remaining risk areas are identifiable and can be addressed incrementally during upcoming provider-read-only integration hardening.
