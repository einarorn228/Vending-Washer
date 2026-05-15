# Kiosk UI Phase 4b — Visual parity refinement notes

> **Status note (updated May 15, 2026):** This plan/note contains historical references to the older dual-mode model. Current behavior is touch-first with optional button-box input via `button_box_enabled`; `kiosk_input_mode`/`input_mode` are legacy compatibility metadata only. See `docs/reference/api-reference.md`, `docs/reference/settings-catalog.md`, and `docs/architecture/ui-state-contract.md` for the current contract.


## Scope completed
This pass refines visual/layout fidelity of the new kiosk screens while preserving all Phase 4 behavior and contracts.

## Files changed
- `frontend/src/kiosk/screens/HomeScreen.jsx`
- `frontend/src/kiosk/screens/SelectMachineScreen.jsx`
- `frontend/src/kiosk/screens/StartingScreen.jsx`
- `frontend/src/kiosk/screens/InUseScreen.jsx`
- `frontend/src/kiosk/screens/ErrorScreen.jsx`
- `frontend/src/kiosk/components/machine/MachineCard.jsx`
- `frontend/src/kiosk/components/machine/MachineStatusBadge.jsx`
- `frontend/src/kiosk/KioskRouter.jsx`
- `frontend/src/kiosk/styles/kiosk.css`
- `docs/plans/kiosk-ui-phase4b-visual-parity-notes.md`

## Visual/layout changes made
1. **Home screen redesigned as large scan-focused hero state**
   - Replaced generic welcome block with a large central hero card.
   - Increased headline size and hierarchy around “Scan your code”.
   - Added single secondary guidance card for mode-specific next-step text.

2. **Select screen refined to kiosk-like machine chooser**
   - Added strong top hero/instruction block with larger typography.
   - Retained dual-mode copy differences only (tap vs hardware buttons).
   - Updated machine cards to be larger, more tactile, and status-forward.

3. **Starting and in-use screens strengthened for confirmation hierarchy**
   - Added top message hero and separate confirmation/details card.
   - Increased machine name prominence for easier distance readability.
   - Kept content backend-driven; no fake timers/progress values introduced.

4. **Machine cards and badges refined**
   - Cards now carry stronger visual status treatment and larger proportions.
   - Touch mode: available cards are card-level tappable/selectable.
   - Hardware mode: same cards remain read-only with hardware guidance text.

5. **Global kiosk CSS reworked for parity direction**
   - Larger typography scale, deeper spacing, stronger card surfaces.
   - More kiosk-like full-screen hero and confirmation blocks.
   - Reduced “settings/dashboard” feel via presentation-focused hierarchy.

## Design elements now matched more closely
- Big, scan-first home presentation with clear top hierarchy.
- Large, bold machine selection cards with clearer status emphasis.
- Distinct start/confirmation state with stronger machine confirmation card.
- More kiosk-like spacing and typography across all states.

## Functional behavior preserved
- Touch mode still calls `POST /api/touch_select_machine` from selection cards.
- Hardware-button mode remains read-only and does not trigger touch actions.
- No backend contract changes.
- No legacy screen reintroduction.
- No fake timers or invented machine metadata.

## Safe data presentation improvement
- `StartingScreen` and `InUseScreen` now attempt to map `current_machine` id to a friendly machine name using existing `machines[]` data when available.
- If no matching machine name is available, the raw backend value is shown unchanged.

## Remaining compromises
- Hardware selection highlight/focus still cannot be shown deterministically without backend-provided active selection context.
- Exact parity with demo micro-details (e.g., any bespoke iconography/animation in supplied assets) remains limited by the plain CSS/no-new-deps constraint.

## Acceptance readiness statement
- The UI is now **substantially closer** to the supplied design intent and should be considered close to acceptance for this migration phase.
- Any further parity work should likely be small polish iterations rather than structural changes.
