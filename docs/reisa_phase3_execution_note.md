# Reisa Phase 3 Execution Note

## Files changed
- `backend/models/usage_session_model.py` (new)
- `backend/services/usage_session_service.py` (new)
- `backend/models/__init__.py`
- `backend/services/start_orchestrator.py`
- `backend/controllers/machine_control.py`
- `docs/reisa_phase3_execution_note.md` (new)

## What session model was introduced
- Added a durable `UsageSession` model (`usage_sessions` table) intended to capture the local lifecycle timeline for scan/start/commit attempts.
- Core fields implemented:
  - identity/routing: `session_uid`, `provider`, `provider_reference`
  - identifier context: `identifier_type`, `identifier_value_masked`
  - flow context: `machine_id`, `scan_source`, `state`
  - quantity/accounting: `requested_quantity`, `committed_quantity`, `remaining_after_commit`
  - error diagnostics: `error_code`, `error_detail`
  - timing: `created_at`, `updated_at`, `started_at`, `completed_at`
- Added `usage_session_service` helper functions for explicit create/update transitions with practical local state constants:
  - `scanned`, `authorized`, `start_requested`, `start_confirmed`, `commit_ok`, `failed`, `timed_out`.

## What lifecycle points now create/update session rows
- Scan acceptance (`ingest_scan`) now creates a `UsageSession` row in `scanned` state.
- Start orchestration (`start_from_code` / `start_from_button`):
  - reuses prior scan-created session when available (by scanned code) or creates one if needed,
  - updates to `authorized`,
  - updates to `start_requested` after successful local start request,
  - updates to `failed` when start request is rejected.
- Telemetry-confirmed start path (`handle_start_confirmed`):
  - updates to `start_confirmed` when telemetry emits start,
  - updates to `commit_ok` with committed quantity and remaining uses when local provider commit succeeds,
  - updates to `failed` on commit failure/exception.
- Runtime timeout/failure hooks in `machine_control`:
  - selection timeout now updates pending session to `timed_out`,
  - device-offline during pending start now updates pending session to `failed`.

## What still remains only in memory
- UI state container (`UI_STATE`) and related UI timers.
- Pending start in-memory map and timer objects (though each pending start now carries `session_uid` to sync durable updates).
- Armed-code lifecycle and button-selection timer state.
- Telemetry runtime machine state cache in `MachineStateStore`.

## What behavior should remain unchanged
- Scanner, API scan/start, and button flows keep the same public routes/contracts.
- Telemetry-confirmed commit timing is preserved: usage commit still occurs only after telemetry confirms machine start.
- Existing machine control and Shelly relay behavior are unchanged from user perspective.
- Existing UI progression/messages are unchanged except behind-the-scenes durable session writes.

## Risks that remain
- Scan-to-start session linking currently uses a short in-memory code-to-session mapping, so process restarts can break that continuity (a fresh start attempt still creates a new durable row).
- Legacy compatibility entrypoints in `machine_control` still exist and can diverge if modified without orchestrator/session updates.
- Mixed DB session patterns across the codebase are still present.
- Completion-of-cycle (`runstate_stopped`) is not yet persisted into usage sessions (`completed_at`) in this phase.

## Ready for Phase 4?
- **Yes, with expected caveats.**
- The code now has a durable local usage-session timeline across scan acceptance, authorization, start request, telemetry-confirmed start, commit outcome, and timeout/offline failures.
- This provides a practical persistence baseline for introducing next-phase provider enhancements while keeping current local behavior stable.
