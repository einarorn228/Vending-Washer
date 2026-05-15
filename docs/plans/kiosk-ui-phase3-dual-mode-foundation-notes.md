# Kiosk UI Phase 3 — Dual-Mode Foundation Notes

> **Status note (updated May 15, 2026):** This plan/note contains historical references to the older dual-mode model. Current behavior is touch-first with optional button-box input via `button_box_enabled`; `kiosk_input_mode`/`input_mode` are legacy compatibility metadata only. See `docs/reference/api-reference.md`, `docs/reference/settings-catalog.md`, and `docs/architecture/ui-state-contract.md` for the current contract.


## Scope completed
This phase adds contract and plumbing for dual input modes without migrating the current screen set.

## Files added
- `frontend/src/kiosk/adapters/inputModeAdapter.js`
- `frontend/src/kiosk/interaction/createInteractionPolicy.js`
- `docs/plans/kiosk-ui-phase3-dual-mode-foundation-notes.md`

## Files changed
- `frontend/src/kiosk/KioskRouter.jsx`
- `frontend/src/kiosk/adapters/uiStateAdapter.js`
- `backend/controllers/ui_api.py`
- `backend/setup/seed_settings.py`

## Where input mode now comes from
- Backend `GET /api/ui_state` now includes `input_mode`.
- `input_mode` is resolved from settings key `kiosk_input_mode`.
- Allowed values are currently normalized to:
  - `touch`
  - `hardware_buttons`
- Any missing/unknown value is normalized to `hardware_buttons` on the backend.
- Seed defaults now include `kiosk_input_mode=hardware_buttons`.

## Fallback behavior when `input_mode` is missing
- Frontend adapter (`adaptInputMode`) applies an additional safety fallback:
  - missing/invalid `input_mode` => `hardware_buttons`
  - `isFallback: true`
- This ensures read-only hardware-style interaction policy defaults even during partial rollouts.

## Interaction policy fields now available
`createInteractionPolicy` now returns:
- `inputMode`
- `isFallback`
- `isTouchMode`
- `isHardwareButtonsMode`
- `allowTouchPrimaryActions`
- `allowTouchMachineSelect`
- `allowTouchSecondaryActions`

Policy defaults are centralized and not scattered in screen components.

## Router/plumbing updates
- `KioskRouter` now computes `interactionPolicy` once and passes it (plus `inputMode`) at the router/screen boundary.
- Existing state-to-screen mapping and screen rendering remain unchanged.
- Existing polling cadence and connectivity banner behavior remain unchanged.

## Hardware-mode selection highlighting readiness
- Backend currently exposes `input_mode` only.
- Backend does **not** yet expose hardware selection cursor context (e.g., `active_machine_id` for button navigation highlight).
- Therefore, the frontend still cannot safely render hardware selection highlight state without guessing.

## Blockers remaining before full screen migration
1. Add backend-provided hardware selection context (at minimum, active machine id during `choose_machine`) for deterministic highlight behavior.
2. Optionally add backend `interaction`/permissions object if touch actions must be enabled/disabled per state dynamically.
3. Confirm operator/admin workflow for managing `kiosk_input_mode` value in deployed environments.
4. Implement new dual-mode-aware screen components (future phase) using the now-centralized policy.

## Validation summary
### Mode flow trace — touch mode
1. `settings.kiosk_input_mode = touch`
2. `/api/ui_state` returns `input_mode: "touch"`
3. frontend `adaptUiState` preserves `input_mode`
4. `adaptInputMode` resolves touch (no fallback)
5. `createInteractionPolicy` enables touch primary/machine-select policy flags
6. router passes policy to current screens (current visuals unchanged)

### Mode flow trace — hardware button mode
1. `settings.kiosk_input_mode = hardware_buttons`
2. `/api/ui_state` returns `input_mode: "hardware_buttons"`
3. adapter/policy resolve hardware mode
4. policy keeps touch actions disabled/read-only
5. router passes policy to current screens (current visuals unchanged)

### Safe fallback trace — missing/invalid mode
- If backend omits `input_mode` or returns unknown value, frontend defaults to hardware mode with `isFallback: true`.
- Backend also defaults unknown settings values to hardware mode.

### Regression check statement
- Polling interval remains 1000 ms.
- Current UI state routing remains unchanged.
- Current connection banner trigger behavior remains unchanged.
- No full screen replacement or redesign has been performed in this phase.

## Readiness for full screen migration
- **Partially ready.**
- Dual-mode contract plumbing and centralized interaction policy are in place.
- Full migration can begin once backend exposes explicit hardware selection focus/context needed for non-guessing highlight UX.
