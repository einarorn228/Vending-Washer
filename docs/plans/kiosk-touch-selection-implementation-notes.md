# Kiosk touch selection backend contract — implementation notes

> **Status note (updated May 15, 2026):** This plan/note contains historical references to the older dual-mode model. Current behavior is touch-first with optional button-box input via `button_box_enabled`; `kiosk_input_mode`/`input_mode` are legacy compatibility metadata only. See `docs/reference/api-reference.md`, `docs/reference/settings-catalog.md`, and `docs/architecture/ui-state-contract.md` for the current contract.


## Scope completed
Implemented the smallest additive backend contract for touch-mode machine selection without sending raw scan code from frontend.

## Files changed
- `backend/controllers/ui_api.py`
- `backend/services/start_orchestrator.py`
- `backend/tests/test_ui_api.py`
- `docs/reference/api-reference.md`
- `docs/plans/kiosk-touch-selection-implementation-notes.md`

## New endpoint contract
### Endpoint
`POST /api/touch_select_machine`

### Request
```json
{
  "machine_id": "washer1"
}
```

### Success response (`200`)
```json
{
  "success": true,
  "message": "Washer 1 is powered on. Select a program on the machine (max 10 minutes).",
  "uses_left": 1,
  "state": "machine_starting"
}
```

### Failure response shape
```json
{
  "success": false,
  "message": "<reason>",
  "uses_left": null,
  "state": "<current_backend_state>"
}
```

Common status mapping:
- `400`: invalid payload (`machine_id` missing/invalid)
- `409`: precondition/state/mode/session/start conflicts

## Existing backend logic reused
- Reused existing start orchestration internals by introducing a small shared helper in `start_orchestrator`.
- `start_from_button(...)` now delegates to shared `_start_from_machine(...)`.
- New `start_from_touch(machine_id)` uses the same authorization and machine start path as hardware/button flow.
- Existing `start_machine(...)` remains authoritative for machine availability checks and start lifecycle.

## Preconditions enforced
The touch endpoint now enforces all required preconditions:
1. `machine_id` is present.
2. `machine_id` exists in backend machine snapshot.
3. backend input mode is `touch` (`kiosk_input_mode`).
4. backend UI state is `choose_machine`.
5. backend-held armed scan/session context must be valid (otherwise existing orchestration returns `No valid scan in progress.`).
6. machine availability/start feasibility remains validated in existing `start_machine(...)` logic.

## Hardware-button compatibility
Preserved by design:
- `/api/i4_event` contract unchanged.
- Hardware flow still resolves button index -> machine and uses backend-held armed scan context.
- Shared helper only reduces duplication; semantics of button start path are unchanged.

## Validation performed
- Added focused API tests in `backend/tests/test_ui_api.py`:
  - missing/invalid machine id
  - touch-mode gate
  - choose-machine-state gate
  - success path (mocked orchestrator outcome)
  - no-armed-scan rejection (mocked orchestrator outcome)

## Remaining blockers before frontend screen migration
- Frontend still needs to call `POST /api/touch_select_machine` from touch-select UI.
- Optional UX copy tuning may be needed for touch wording vs hardware wording.
- If stricter state context is desired, an optional `selection_context` payload can be added later; not required for this contract step.

## Readiness summary
Backend is now ready for the next frontend migration phase (touch machine-card selection wiring) with a minimal, safe, additive contract that keeps backend session/code authority intact.
