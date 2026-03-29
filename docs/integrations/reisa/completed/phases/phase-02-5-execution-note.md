# Reisa Phase 2.5 Execution Note

## Files changed
- `backend/controllers/machine_control.py`
- `backend/services/start_orchestrator.py`
- `docs/reisa_phase2_5_execution_note.md` (new)

## What remaining local entitlement paths were cleaned up
- Reworked `machine_control.validate_code(...)` to delegate local entitlement lookup/authorization through `LocalProvider` instead of querying `Code` directly.
- Reworked `machine_control._apply_usage_delta(...)` to delegate usage commit through `LocalProvider.commit_start(...)` (legacy helper retained only as compatibility wrapper for older internal call sites).
- Updated button-trigger orchestration path (`start_orchestrator.start_from_button`) to use provider authorization before machine start, reducing special-case direct validation logic in the button flow.
- Added thin button-runtime helpers in `machine_control` (`resolve_button_machine`, `get_button_start_code`) so button flow coordination can live in orchestrator while machine-control keeps hardware/runtime/event concerns.

## What still intentionally remains outside provider/orchestrator
- Runtime and hardware control (`MachineStateStore`, Shelly relay on/off, pending-start tracking, scanner/button hardware interaction).
- UI state transitions and display messaging.
- Scan logging and metrics plumbing.
- Armed-code lifecycle and timeout behavior.

These remain in `machine_control` by design for now to avoid broad risk while Phase 2.5 focuses on entitlement authority cleanup.

## What behavior should remain unchanged
- Scanner ingress (`/api/scan_code` and serial scanner) still uses the same visible flow and messages.
- Explicit code start and button start still use existing route contracts.
- Local DB-backed validity and usage rules remain the authority.
- Usage decrement still occurs only after telemetry confirms machine start.
- UI state progression and start timing behavior remain unchanged.

## Risks that remain
- Legacy button helpers (`start_machine_from_button`, `handle_i4_button`) still exist for compatibility and can diverge if modified later.
- In-memory state (`UI_STATE`, `_pending_starts`, armed code) is still process-local.
- Session/idempotency modeling is still deferred to the next phase.
- Mixed DB session usage patterns remain in the broader codebase.

## Is the code now ready for Phase 3?
- **Yes, conditionally.**
- Local entitlement authority is now more consistently centralized behind `LocalProvider`, and orchestrator/provider boundaries are more coherent across explicit start, scan validation path, and button-triggered start.
- The codebase is better prepared for Phase 3 session-model extraction without introducing Reisa or usage-session persistence yet.
