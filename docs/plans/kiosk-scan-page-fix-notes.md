# Kiosk Scan Page Fix Notes

## Files changed
- `frontend/src/kiosk/screens/HomeScreen.jsx`
- `frontend/src/kiosk/components/chrome/KioskProgressSteps.jsx`
- `frontend/src/kiosk/components/machine/MachineGrid.jsx`
- `frontend/src/kiosk/components/machine/MachineCard.jsx`
- `frontend/src/kiosk/components/machine/MachineStatusBadge.jsx`
- `frontend/src/kiosk/styles/kiosk.css`

## What was wrong with the previous Scan page
- The waiting-for-code page used a bright blue hero style that did not match the supplied dark screenshot direction.
- It included a separate “Next step” detail card, which should not be on this page.
- The top progress looked like a pill-style progress bar instead of clean circular steps.
- Machine cards looked like generic stacked kiosk/admin tiles and did not match the screenshot’s wide horizontal status-card treatment.
- The scan hero icon and spacing did not match the calm, minimal scan-card composition from the screenshot.

## What was changed to match the screenshot
- Reworked `HomeScreen` for `waiting_for_code` to only render:
  1. a large centered scan hero card,
  2. a status-only machine grid below.
- Removed the old “Next step” card from the Scan page.
- Reworked the stepper visuals to circular numbered steps (Scan / Select / Start) with subtle connectors.
- Added a CSS-based scan icon block to the hero card (no new dependencies/assets).
- Updated scan-page machine cards to be wider, horizontal kiosk status cards with:
  - left-side machine icon treatment,
  - large machine name,
  - status badge copy in English (`Available`, `In use`).
- Ensured this page remains read-only status display by passing `isInteractive={false}` on the Scan page.

## Shared machine styling adjustments
- Shared machine components were updated to support a **variant** model:
  - `MachineGrid` now accepts `variant`.
  - `MachineCard` now accepts `variant` and uses `scan`-specific presentation.
- Existing non-scan screens continue to use the default machine card variant and interaction logic.

## Scan-page-specific variant introduced
- Yes. `variant="scan"` was introduced on the waiting-for-code page and wired through:
  - `HomeScreen` -> `MachineGrid` -> `MachineCard`.

## Remaining tiny differences from screenshot
- The exact top-right debug controls in the screenshot are outside the scan-page component itself and were not reimplemented as part of this focused page correction.
- Minor font/rendering differences may still exist depending on runtime font availability and viewport scaling.
