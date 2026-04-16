# Kiosk UI Final Polish Notes

## Files changed
- `frontend/src/kiosk/KioskRouter.jsx`
- `frontend/src/kiosk/KioskAppShell.jsx`
- `frontend/src/kiosk/styles/kiosk.css`
- `frontend/src/kiosk/components/chrome/ConnectionBanner.jsx`
- `frontend/src/kiosk/components/chrome/KioskHeader.jsx`
- `frontend/src/kiosk/components/chrome/KioskFooter.jsx`
- `frontend/src/kiosk/components/chrome/KioskProgressSteps.jsx` (new)
- `frontend/src/kiosk/screens/HomeScreen.jsx`
- `frontend/src/kiosk/screens/SelectMachineScreen.jsx`
- `frontend/src/kiosk/screens/StartingScreen.jsx`
- `frontend/src/kiosk/screens/InUseScreen.jsx`
- `frontend/src/kiosk/screens/ErrorScreen.jsx`
- `frontend/src/kiosk/components/machine/MachineCard.jsx`
- `frontend/src/kiosk/components/machine/MachineStatusBadge.jsx`
- `frontend/src/kiosk/components/machine/normalizeMachineStatus.js`
- `docs/plans/kiosk-ui-final-polish-notes.md` (new)

## What was taken from each reference direction
### Taken from reference variant 2
- Added a clear top progress treatment (`Scan / Select / Start`) to strengthen flow identity.
- Kept the two-tier screen structure in key states (top message/hero card + bottom detail card).
- Preserved the large scan-first hero on the home screen.
- Kept concise, plain English state wording.

### Taken from reference variant 1
- Increased visual weight and contrast for a stronger kiosk presence.
- Made machine cards larger and more tactile, with richer status hierarchy.
- Improved transient feedback feel via styled status toast in selection flow.
- Increased drama in scan/start visual hierarchy while staying dependency-free.
- Strengthened distinction between machine status treatments.

## Visual refinements made
- Introduced a shared shell top bar with progress stepper and polished chrome balance.
- Redesigned home hero around a CSS-based scan identity element for stronger scan-first framing.
- Refined machine selection hierarchy with larger cards, clearer action hints, and stateful badges.
- Improved start and in-use confirmation to a stronger two-card composition.
- Tightened error state severity styling while preserving readability.
- Kept backend unreachable banner behavior but translated and simplified copy into English.

## English copy decisions
- Standardized copy to short kiosk phrases:
  - “Scan your code”
  - “Choose your machine”
  - “Machine enabled”
  - “Machine running”
  - “Unable to continue”
- Kept mode-specific guidance concise and secondary.
- Removed Icelandic/legacy technical phrasing from visible kiosk UI text.

## Compromises that still remain
- Hardware active-selection highlight is still not shown because backend does not provide selection cursor context.
- No countdown/progress timer is shown because backend does not provide timer fields.
- Status badge richness beyond available/busy uses optional backend `machine.status` only if present; no frontend-only status fabrication was added.

## Acceptance readiness
- The kiosk UI is now substantially closer to the target direction and is ready for acceptance review.
- Remaining gaps are small and backend-contract-driven, not layout-system blockers.

## Validation summary
- All modified visible kiosk copy is English-only.
- Touch mode machine select still uses `POST /api/touch_select_machine` via existing frontend API helper.
- Hardware mode remains read-only because touch selection is still gated by interaction policy.
- No backend contract changes were required in this polish pass.
- No fake timers or invented machine metadata were added.


## Final micro-fix pass
- Added a shared machine status normalization helper and now use it in both `MachineCard` and `MachineStatusBadge` so badge and card class styling always align.
- Added safe alias mapping for likely backend variants (`in_use`, `occupied`, `unavailable`) to `busy`.
- Updated progress step behavior so the stepper is hidden in `error` state, avoiding a misleading default highlight on “Scan”.
- No backend/API contract changes were needed for this pass.

### Final acceptance check
- Card styling and badge styling now use one normalization path across all supported statuses (`available`, `busy`, `reserved`, `error`).
- Error state no longer visually implies the flow is back at the Scan step.
- No functional UI mismatches are currently known in this scope; UI is ready for acceptance.
