# Kiosk UI Phase 4 — Screen Migration Notes

> **Status note (updated May 15, 2026):** This plan/note contains historical references to the older dual-mode model. Current behavior is touch-first with optional button-box input via `button_box_enabled`; `kiosk_input_mode`/`input_mode` are legacy compatibility metadata only. See `docs/reference/api-reference.md`, `docs/reference/settings-catalog.md`, and `docs/architecture/ui-state-contract.md` for the current contract.


## Scope completed
Phase 4 replaces legacy kiosk screen components in router flow with new design-specific screen components while preserving backend authority and dual-mode behavior.

## Files added
- `frontend/src/kiosk/screens/HomeScreen.jsx`
- `frontend/src/kiosk/screens/SelectMachineScreen.jsx`
- `frontend/src/kiosk/screens/StartingScreen.jsx`
- `frontend/src/kiosk/screens/InUseScreen.jsx`
- `frontend/src/kiosk/screens/ErrorScreen.jsx`
- `frontend/src/kiosk/components/machine/MachineGrid.jsx`
- `frontend/src/kiosk/components/machine/MachineCard.jsx`
- `frontend/src/kiosk/components/machine/MachineStatusBadge.jsx`
- `docs/plans/kiosk-ui-phase4-screen-migration-notes.md`

## Files changed
- `frontend/src/kiosk/KioskRouter.jsx`
- `frontend/src/api/backend.js`
- `frontend/src/kiosk/styles/kiosk.css`

## Legacy screen replacement map
- `ScanScreen` replaced by `HomeScreen` for `waiting_for_code`.
- `MachineSelectScreen` replaced by `SelectMachineScreen` for `choose_machine`.
- `ResultScreen` split and replaced by:
  - `StartingScreen` for `machine_starting`
  - `InUseScreen` for `machine_in_use`
  - `ErrorScreen` for `error`
  - `ErrorScreen` fallback for unknown states.

## Touch mode behavior now
- In `choose_machine`, cards are tappable when `interactionPolicy.allowTouchMachineSelect` is true.
- Tapping a card calls `POST /api/touch_select_machine` via new frontend helper `touchSelectMachine(machineId)`.
- Request uses backend-held session context only; no raw scan code is sent by frontend.
- Endpoint failures return user-facing status text in the selection status panel.

## Hardware-button mode behavior now
- Uses same screen layout and machine cards for parity.
- Cards render as non-interactive in hardware mode.
- Instructional copy explicitly tells user to continue with hardware buttons.
- No touch-selection endpoint calls are made in hardware mode because interaction policy disables selection.

## Design parity notes (implemented)
- Unified kiosk shell/chrome from earlier phases remains in place.
- New screen hierarchy and card/grid presentation now align with design intent:
  - clear instruction block
  - machine card grid with status badge and action/read-only region
  - state-specific status panels for starting/in-use/error paths
- Touch and hardware modes share the same structural layout; only guidance/action affordance changes.

## Contract-limited compromises
- No hardware selection highlight/focus is rendered because backend still does not provide an active hardware cursor field (e.g., `active_machine_id`).
- No countdown/progress timer is shown because backend does not provide a timer value and frontend does not fake timers.
- `current_machine` can be unavailable in some backend states, so starting/in-use screens fall back to neutral text when needed.

## Further backend work still needed?
- **Not required** to complete this migration scope.
- **Recommended** for higher parity later:
  1. Add hardware selection context (`active_machine_id`) for deterministic hardware highlight.
  2. Optionally add explicit interaction permissions per state if operations need runtime gating beyond `input_mode`.
