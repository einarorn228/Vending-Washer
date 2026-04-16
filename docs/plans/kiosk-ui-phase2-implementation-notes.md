# Kiosk UI Phase 2 — Implementation Notes

## Files added
- `frontend/src/kiosk/KioskAppShell.jsx`
- `frontend/src/kiosk/components/chrome/ConnectionBanner.jsx`
- `frontend/src/kiosk/components/chrome/KioskHeader.jsx`
- `frontend/src/kiosk/components/chrome/KioskFooter.jsx`
- `frontend/src/kiosk/components/feedback/InstructionBlock.jsx`
- `frontend/src/kiosk/components/feedback/StatusPanel.jsx`
- `frontend/src/kiosk/styles/kiosk.css`

## Files changed
- `frontend/src/kiosk/KioskRouter.jsx`

## Visual foundation introduced
- Added a reusable kiosk shell structure with shared chrome regions:
  - top connection banner region
  - persistent kiosk header
  - main content area for state-driven screens
  - persistent kiosk footer
- Added shared feedback primitives (`InstructionBlock`, `StatusPanel`) for upcoming screen-specific composition in Phase 3.
- Added a lightweight CSS foundation with variables for colors, spacing surfaces, typography defaults, banner styling, and reusable block/panel styles.

## Behavior intentionally unchanged
- Polling behavior remains in `useUiStatePolling` with the same 1000 ms interval.
- Backend unreachable handling remains a boolean flag driven by poll failures and successful recovery.
- UI state routing remains unchanged:
  - `waiting_for_code` -> `ScanScreen`
  - `choose_machine` -> `MachineSelectScreen`
  - `machine_starting`, `machine_in_use`, `error` -> `ResultScreen`
  - unknown states fallback to `ResultScreen` with `message || ''`
- Legacy screens remain responsible for primary per-state content rendering.
- No backend files were changed.
- No API contract fields or request/response behavior were changed.

## Known gaps before Phase 3
- Legacy screens still use inline styling and are not yet migrated to the final design-specific per-screen components.
- Shared feedback primitives are introduced but not yet deeply applied to each state-specific screen layout.
- Machine-card-level visual parity and richer state badges are not implemented yet.

## Backend-unreachable banner logic mismatch assessment
- No semantic mismatch introduced in this phase.
- Banner content, trigger condition, and recovery behavior are preserved; only componentized and styled via shared chrome/CSS.

## Phase 3 readiness summary
- The app now has a centralized shell/chrome structure and reusable feedback primitives that can be used to migrate screens one-by-one with reduced duplication while keeping existing behavior stable.
