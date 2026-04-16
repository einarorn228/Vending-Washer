# Kiosk UI Phase 1 — Implementation Notes

## Files added
- `frontend/src/kiosk/hooks/useUiStatePolling.js`
- `frontend/src/kiosk/KioskRouter.jsx`
- `frontend/src/kiosk/adapters/uiStateAdapter.js`

## Files changed
- `frontend/src/App.jsx`

## Behavior intentionally preserved
- Polling still runs every 1000 ms (`setInterval(..., 1000)`).
- Poll failures still mark backend as unreachable.
- Last known UI state is retained when polling fails (stale UI behavior preserved).
- Backend state-to-screen mapping is unchanged:
  - `waiting_for_code` -> `ScanScreen`
  - `choose_machine` -> `MachineSelectScreen`
  - `machine_starting`, `machine_in_use`, `error` -> `ResultScreen`
- Unknown states still fall back to `ResultScreen` with `message || ''`.
- The backend-unreachable banner content and styling are preserved.

## Technical decisions
- Extracted polling logic into `useUiStatePolling` to isolate side effects from rendering.
- Extracted state-to-screen rendering into `KioskRouter` to centralize routing behavior.
- Added a thin `adaptUiState` pass-through adapter that only normalizes `state`/`message` to strings when present and returns `null` for invalid payloads.
- Kept existing screen components unchanged and in use for Phase 1.

## Risks / follow-up notes for Phase 2
- `adaptUiState` currently performs only minimal normalization by design; richer normalization should wait for explicit contract decisions.
- Connectivity metadata is still limited to a boolean flag; Phase 2 may introduce richer stale timing UX if needed.
- The banner remains inside the router for parity; Phase 2 could extract shared kiosk chrome components once visual work starts.
