# Kiosk UI Integration Plan (Design-Specific, Documentation-First)

> **Status note (updated May 15, 2026):** This plan/note contains historical references to the older dual-mode model. Current behavior is touch-first with optional button-box input via `button_box_enabled`; `kiosk_input_mode`/`input_mode` are legacy compatibility metadata only. See `docs/reference/api-reference.md`, `docs/reference/settings-catalog.md`, and `docs/architecture/ui-state-contract.md` for the current contract.


## Scope and intent
This plan defines a safe migration path for integrating the new kiosk UI into the existing app **without changing runtime behavior prematurely**.

### Design source of truth (explicit)
The target UI in this plan is based on:
1. the **supplied React demo component**, and
2. the **supplied screenshots** for home / machine-select / start states.

The implementation goal is **close visual parity** with those supplied artifacts, **not** a loose reinterpretation.

### Non-goals in this step
- No frontend or backend feature coding yet.
- No contract-breaking backend edits yet.
- This document is implementation-oriented prep only.

### Input mode requirement (new, explicit)
The kiosk UI must support two operation modes while keeping the visual design essentially the same:

1. **Touch mode**
   - User interacts directly with on-screen controls.
   - Machine selection and other actions can be triggered from touchscreen UI.
2. **Hardware button mode**
   - UI visuals remain nearly identical to touch mode.
   - User does **not** drive flow through touchscreen interactions.
   - Existing physical button box / hardware controls drive state and actions.
   - Screen acts as a visual guide + status display for backend/hardware-driven events.

Core rule for all phases in this plan: **layout and visual hierarchy should stay consistent across modes; only the action/input source changes.**

---

## 1) Current architecture baseline

### 1.1 Frontend entry points and kiosk components
- `frontend/src/index.jsx` mounts `<App />`.
- `frontend/src/App.jsx` owns polling loop, state switch, and backend connectivity banner.
- Screen components today:
  - `frontend/src/components/ScanScreen.jsx`
  - `frontend/src/components/MachineSelectScreen.jsx`
  - `frontend/src/components/ResultScreen.jsx`

### 1.2 Frontend state model today
- `App.jsx` stores `uiState` and `backendUnreachable`.
- Polls `pollState()` every 1000 ms.
- `pollState()` calls `/api/ui_state` via `frontend/src/api/backend.js`.
- Null response => stale UI retained + warning banner.

### 1.3 Backend-driven UI state model today
Backend owns state machine in `backend/controllers/machine_control.py` (`UI_STATE`).
Observed states:
- `waiting_for_code`
- `choose_machine`
- `machine_starting`
- `machine_in_use`
- `error`

Exposed via `GET /api/ui_state` in `backend/controllers/ui_api.py`, which refreshes `machines` from telemetry snapshot.

### 1.4 Frontend contract dependencies (current)
Current frontend rendering depends on:
- `state`
- `message`
- `machines[]` with `{ id, name, available }`
- (present but minimally used visually) `uses_left`, `current_machine`

---

## 2) Design-to-implementation mapping (supplied design specific)

> This section maps **target screens/elements/behaviors from supplied demo + screenshots** to current implementation and gaps.

### 2.1 Screen mapping

| Target design screen | Current frontend mapping | Required new components | Backend fields needed | Support status |
|---|---|---|---|---|
| Home / idle scan state | `waiting_for_code` -> `ScanScreen` | `kiosk/screens/HomeScreen.jsx`, `kiosk/components/chrome/KioskShell.jsx` | `state`, `message` | Partially supported (visual redesign missing) |
| Machine selection state | `choose_machine` -> `MachineSelectScreen` | `kiosk/screens/SelectMachineScreen.jsx`, `MachineGrid`, `MachineCard`, `StatusBadge` | `machines[]`, `message`, optional richer status fields | Partially supported (data shape limited) |
| Start confirmation / in-progress state | `machine_starting` + `machine_in_use` -> `ResultScreen` | `kiosk/screens/StartingScreen.jsx`, `kiosk/screens/InUseScreen.jsx` | `state`, `message`, `current_machine`, `uses_left`, optional timer fields | Partially supported (single generic screen today) |
| Error state | `error` -> `ResultScreen` | `kiosk/screens/ErrorScreen.jsx`, shared `StatusPanel` | `state`, `message` | Supported for logic, missing parity visuals |

### 2.2 Major visual element mapping

| Target design element | Existing code location | Required new component(s) | Backend dependency | Status |
|---|---|---|---|---|
| Full-screen kiosk frame/chrome | none (inline styles only) | `KioskShell`, optional `KioskHeader`, `KioskFooter` | none | Missing |
| Branded title/subtitle hierarchy | scattered `h1` text | `InstructionBlock` | `message` + optional secondary message | Missing |
| Machine cards with richer badges | `MachineSelectScreen.jsx` text list | `MachineCard`, `MachineStatusBadge`, `MachineGrid` | currently `available`; optional `status` for full fidelity | Missing |
| Start status card (machine + progress text) | `ResultScreen.jsx` generic `h1` | `StartStatusPanel` | `state`, `current_machine`, `message` | Missing |
| Connection quality banner/toast | inline banner in `App.jsx` | `ConnectionBanner` reusable component | frontend-only from poll failures | Present but should be refactored |

### 2.3 Major behavior mapping

| Target behavior | Current behavior source | Required implementation path | Backend dependency | Status |
|---|---|---|---|---|
| Auto-refresh UI from backend | `App.jsx` interval + `pollState` | move into `useUiStatePolling` hook | `/api/ui_state` | Supported |
| Render by backend state only | `App.jsx` switch | `KioskRouter` + adapter | `state` | Supported |
| Show machine availability in select state | `MachineSelectScreen.jsx` | card-based rendering preserving backend truth | `machines[].available` | Supported (limited semantics) |
| Distinct visual treatment for starting vs in-use | currently same `ResultScreen` | split to dedicated state screens | `state` + machine context | Missing |
| Graceful stale/offline indicator | banner flag in `App.jsx` | reusable stale-state indicator + timestamp | frontend polling metadata | Partially supported |

### 2.4 Input mode screen behavior mapping (touch vs hardware button)

| Screen/state | Touch mode behavior | Hardware button mode behavior | Shared visual requirement |
|---|---|---|---|
| Home (`waiting_for_code`) | Optional touch affordance can remain inert or active for scan/help actions if defined. | No primary control via touch; wait for scan/hardware/backend events. | Same headline, branding, and status framing. |
| Machine select (`choose_machine`) | User taps a machine card/button to request selection. | Cards are non-interactive; selection/highlight follows backend-reported active selection and hardware navigation. | Same grid/card layout and status badges. |
| Starting (`machine_starting`) | Touch may allow safe secondary actions only if backend permits (generally read-only). | Fully read-only; backend/hardware events progress state. | Same progress/status panel and machine context. |
| In use (`machine_in_use`) | Mostly read-only; touch actions only if explicitly backend-authorized. | Read-only visual guidance driven by backend updates. | Same status/info hierarchy. |
| Error (`error`) | Touch retry/ack only if backend contract explicitly supports it. | Read-only until backend/hardware clears/resets state. | Same error prominence and instruction block. |

Instruction text should remain very similar between modes, with only targeted wording changes where needed (for example: “Tap a machine” vs “Use hardware buttons to choose a machine”).

---

## 3) Styling strategy decision (for supplied design parity)

### Option A: Adopt Tailwind + framer-motion + lucide-react
**Pros**
- Faster parity with typical modern demo component patterns.
- Utility-first styling can mirror supplied component quickly.
- `framer-motion` helps match micro-transitions from demo patterns.
- `lucide-react` aligns with common icon usage in kiosk demos.

**Cons / risks**
- Introduces 3 dependencies and build config changes.
- Higher migration risk while functional parity is still being validated.
- Motion could impact lower-powered kiosk hardware if overused.

### Option B: Translate supplied design into plain CSS/CSS modules (JSX only)
**Pros**
- Lowest dependency risk.
- Keeps bundle/runtime simpler for kiosk environment.
- Easier to control deterministic styles and performance.

**Cons**
- More manual work to match certain utility-style details.
- Custom animation primitives may take longer to polish.

### Recommendation
Use a **hybrid staged strategy**:
1. **Phase 1–3:** Implement parity-first screens using JSX + plain CSS/CSS modules (no new UI libraries).
2. **Optional Phase 4+ enhancement:** add minimal libraries only if parity gaps remain (icons first, motion second).

Reason: safer rollout, easier debugging, and fewer moving parts while backend contract and state fidelity are being verified.

---

## 4) Backend contract gap table (implementation-critical)

| Required UI field for new design | Current backend field | Frontend derivable safely? | Backend change needed? | Notes |
|---|---|---|---|---|
| Global screen state | `state` | n/a | No | Already authoritative. |
| Primary user instruction text | `message` | n/a | No | Already authoritative. |
| Machine list | `machines[]` | n/a | No | Present today. |
| Machine availability badge | `machines[].available` (bool) | Partially (bool -> label) | Maybe | Full parity may need enum status (e.g., offline/starting/in_use). |
| Machine display name | `machines[].name` | n/a | No | Present. |
| Machine identity key | `machines[].id` | n/a | No | Present. |
| Currently selected machine label | `current_machine` (slug) | Partially (lookup from machines[]) | Maybe | May need explicit `current_machine_name`. |
| Remaining uses display | `uses_left` | n/a | No | Present; ensure all states populate consistently. |
| Selection timeout countdown | none (timeout configured server-side) | No (cannot safely infer remaining server timer) | **Yes (likely)** | Need backend-provided remaining seconds for exact parity. |
| Poll staleness timestamp | none | Frontend can track local last success | No (optional) | local-only acceptable for connectivity UX. |
| Machine sort/display order | none explicit | Not safely if order must be fixed by backend | **Yes (likely)** | Add backend display ordering if design requires deterministic order. |
| Machine icon/metadata | none | No | Maybe | Needed only if supplied design includes per-machine art/icon semantics. |
| Input mode (`touch` or `hardware_buttons`) | none | No | **Yes (recommended)** | Should be backend-provided to keep kiosk behavior fleet-configurable and authoritative. |
| Hardware selection cursor/current focus | none explicit | Not safely | **Yes (likely)** | Needed in hardware mode so frontend can highlight currently selected machine without local guesswork. |
| Per-screen interaction permissions | none explicit | Not safely | Maybe | Optional field set if backend must dynamically disable/enable specific touch actions. |

**Contract principle:** backend remains source of truth; frontend should not invent machine operational states.

### 4.1 Input mode source-of-truth decision and gap closure

**Recommended source of truth:** backend configuration exposed in `/api/ui_state` (or a closely related config endpoint consumed alongside it).

Why this is safest:
- Prevents frontend divergence from deployed hardware capabilities.
- Supports mixed fleet rollout (some kiosks touch-enabled, others hardware-button-only) without rebuilding frontend.
- Keeps control behavior aligned with the same authority that already drives UI state transitions.

Recommended payload additions (minimum viable):
- `input_mode`: enum string (`"touch"` or `"hardware_buttons"`).
- `interaction`: optional object for explicit gating, e.g.:
  - `allow_touch_machine_select` (bool)
  - `allow_touch_secondary_actions` (bool)
- `selection_context` (optional, primarily for hardware mode):
  - `active_machine_id` (string)
  - `selection_hint` (string; optional instruction override)

Fallback policy if fields are temporarily absent during rollout:
1. Default to safest behavior (`hardware_buttons`-style read-only interactions).
2. Continue rendering same layouts.
3. Log/telemetry warning for missing mode field.

---

## 5) Target frontend architecture (specific to this migration)

Recommended structure:

```text
frontend/src/
  App.jsx
  index.jsx
  api/
    backend.js
    uiStateApi.js
  kiosk/
    KioskRouter.jsx
    KioskAppShell.jsx
    hooks/
      useUiStatePolling.js
    adapters/
      uiStateAdapter.js
      inputModeAdapter.js
    interaction/
      createInteractionPolicy.js
    screens/
      HomeScreen.jsx
      SelectMachineScreen.jsx
      StartingScreen.jsx
      InUseScreen.jsx
      ErrorScreen.jsx
    components/
      chrome/
        ConnectionBanner.jsx
        KioskHeader.jsx
        KioskFooter.jsx
      machine/
        MachineGrid.jsx
        MachineCard.jsx
        MachineStatusBadge.jsx
      feedback/
        InstructionBlock.jsx
        StatusPanel.jsx
    styles/
      kiosk.css
      tokens.js
```

This split keeps behavior wiring separate from visual composition, improving rollout safety.

### 5.1 Input-mode-aware interaction layer (avoid scattered conditionals)

To avoid spreading `if (inputMode === ...)` checks across every component:

1. Normalize backend payload once in `inputModeAdapter.js` and `uiStateAdapter.js`.
2. Build a centralized interaction policy (`createInteractionPolicy.js`) that outputs a small capability object, e.g.:
   - `canTapMachine`
   - `canTapPrimaryAction`
   - `isReadOnlyGuidance`
3. Pass this policy down via router/screen props (or a focused context) so leaf components only consume booleans and labels.
4. Keep screens structurally identical; only interactive props (`onClick`, `disabled`, focus highlight source, helper copy) differ by policy.

This preserves visual parity while making input source behavior explicit, testable, and maintainable.

---

## 6) Refined implementation phases (safe, sequential)

## Phase 0 — Contract and design lock
**Goal**
- Freeze what “close visual parity” means from supplied demo/screenshots and align to current contract.

**Files likely touched**
- `docs/plans/kiosk-ui-integration-plan.md`
- `docs/architecture/ui-state-contract.md` (if clarifications needed)

**Exact deliverables**
- Final mapping checklist: each design element marked supported/missing.
- Backend contract delta list prioritized by must-have vs nice-to-have.

**Acceptance criteria**
- No ambiguous screen/element ownership remains.
- Contract change candidates approved before coding.

## Phase 1 — Non-visual architecture extraction (no UX change)
**Goal**
- Extract polling/router/adapter infrastructure while preserving exact current visuals.

**Files likely touched**
- `frontend/src/App.jsx`
- `frontend/src/api/backend.js`
- `frontend/src/kiosk/hooks/useUiStatePolling.js`
- `frontend/src/kiosk/KioskRouter.jsx`
- `frontend/src/kiosk/adapters/uiStateAdapter.js`

**Exact deliverables**
- Polling hook returns ui state + connectivity metadata.
- Router handles all known backend states + fallback.
- Existing screens still render same text/flow.

**Acceptance criteria**
- Behavior parity with current kiosk app.
- No endpoint/contract changes.

## Phase 2 — Shell + reusable UI primitives
**Goal**
- Introduce design-conformant layout primitives used across all screens.

**Files likely touched**
- `frontend/src/kiosk/KioskAppShell.jsx`
- `frontend/src/kiosk/components/chrome/*`
- `frontend/src/kiosk/components/feedback/*`
- `frontend/src/kiosk/styles/kiosk.css`

**Exact deliverables**
- Kiosk shell layout
- reusable instruction/status/connectivity components
- style tokens and baseline typography/spacing/colors

**Acceptance criteria**
- Existing state flow still works through new shell.
- No regression in backend-unreachable handling.

## Phase 3 — Dual-mode foundation before full screen migration
**Goal**
- Add input mode contract handling + interaction policy plumbing before migrating all screens.

**Files likely touched**
- `frontend/src/kiosk/adapters/uiStateAdapter.js`
- `frontend/src/kiosk/adapters/inputModeAdapter.js`
- `frontend/src/kiosk/interaction/createInteractionPolicy.js`
- `frontend/src/kiosk/KioskRouter.jsx`
- `docs/architecture/ui-state-contract.md`
- `backend/controllers/ui_api.py` (if adding `input_mode` now)

**Exact deliverables**
- Normalized input mode available at router level.
- Centralized interaction policy provided to screen layer.
- Backend/config contract decision implemented or explicitly staged with fallback.

**Acceptance criteria**
- Touch/hardware mode behavior differences are represented in one policy layer, not scattered screen code.
- Default-safe behavior defined when mode is missing.
- Ready for screen migration with dual-mode support from first migrated screen.

## Phase 4 — Screen-by-screen parity migration (built dual-mode from day one)
**Goal**
- Replace legacy screens with design-matching screens in controlled order.

**Files likely touched**
- `frontend/src/kiosk/screens/HomeScreen.jsx`
- `frontend/src/kiosk/screens/SelectMachineScreen.jsx`
- `frontend/src/kiosk/screens/StartingScreen.jsx`
- `frontend/src/kiosk/screens/InUseScreen.jsx`
- `frontend/src/kiosk/screens/ErrorScreen.jsx`
- `frontend/src/kiosk/components/machine/*`

**Exact deliverables**
- Home, select, starting/in-use, error screens with near-parity structure and styling.
- machine cards/badges driven by backend payload.
- each screen supports both input modes without major layout divergence.
- mode-aware instruction copy variants integrated where needed.

**Acceptance criteria**
- All backend states render distinct intended screens.
- Visual parity acceptable against supplied screenshots.
- Machine selection behavior is tap-driven in touch mode and backend/hardware-driven in hardware button mode.

## Phase 5 — Backend contract extensions (only if required)
**Goal**
- Add minimal API fields needed for strict parity where frontend cannot safely derive values.

**Files likely touched**
- `backend/controllers/ui_api.py`
- `backend/controllers/machine_control.py`
- `backend/controllers/telemetry.py` (if richer status exposed)
- `docs/architecture/ui-state-contract.md`
- `docs/reference/api-reference.md`

**Exact deliverables**
- Additional `/api/ui_state` fields (only approved set).
- Contract docs updated with examples and semantics.

**Acceptance criteria**
- Backward compatibility preserved.
- New fields covered by safe frontend fallbacks.

## Phase 6 — Cutover and legacy cleanup
**Goal**
- Make new kiosk UI default and remove outdated paths.

**Files likely touched**
- `frontend/src/components/ScanScreen.jsx`
- `frontend/src/components/MachineSelectScreen.jsx`
- `frontend/src/components/ResultScreen.jsx`
- `frontend/src/App.jsx`

**Exact deliverables**
- legacy components removed (or archived)
- router points only to new screen set
- docs aligned to final architecture

**Acceptance criteria**
- No dead state branches.
- Production operator flow validated end-to-end.

---

## 7) Risks and unknowns

1. Supplied design artifacts are external to repo; parity judgment can drift unless checklist is frozen.
2. Current backend machine payload may be too minimal for strict visual semantics.
3. Timer-based flows in backend are authoritative; frontend countdown visuals need backend-sourced timing to avoid drift.
4. Polling-only architecture can cause visual lag; UI should visibly handle stale-state periods.
5. Dependency additions can increase rollout complexity on kiosk hardware.

---

## 8) Test checklist by phase

### Phase 1 (architecture extraction)
- polling still every 1s
- state routing unchanged for all known backend states
- unknown state falls back safely
- backend outage shows warning and recovers cleanly

### Phase 2 (shell/primitives)
- shell does not break any state transitions
- connection banner still appears on failures
- typography/layout consistent in kiosk viewport

### Phase 3 (dual-mode foundation)
- input mode is normalized once and available at router/screen boundary
- interaction capability policy is centralized and unit-testable
- missing input mode falls back to safe read-only interaction policy
- no visual layout branching introduced solely by input mode

### Phase 4 (screen parity)
- `waiting_for_code` matches home screenshot intent
- `choose_machine` matches select screenshot intent and machine availability truth
- `choose_machine` tap-to-select works in touch mode
- `choose_machine` renders non-tappable cards + backend-driven highlight/instructions in hardware mode
- `machine_starting` and `machine_in_use` visually distinct and correct
- `error` remains prominent and resets correctly

### Phase 5 (contract changes if any)
- each new backend field appears in `/api/ui_state` as documented
- frontend falls back safely when field absent
- no regressions to existing API clients

### Phase 6 (cutover)
- full flow: valid scan -> select -> start -> in_use -> reset
- invalid scan -> error -> reset
- busy scan rejection and timeout paths remain user-clear

---

## 9) Short decision: best representation of input mode in code

**Decision:** represent input mode as a backend-provided enum (`input_mode`) that is normalized into a typed frontend domain value and converted into a centralized interaction capability policy.

**Why this approach**
- Preserves backend authority and operational safety.
- Keeps screens mostly presentation-focused and visually consistent.
- Avoids widespread conditional logic and regression-prone ad-hoc checks.
- Supports phased rollout with safe default behavior when config is incomplete.

---

## Phase 1 next action

Before coding starts, execute this exact prep checklist.

### A) Exact files to inspect/change first
1. Inspect (read-only first):
   - `frontend/src/App.jsx`
   - `frontend/src/api/backend.js`
   - `frontend/src/components/ScanScreen.jsx`
   - `frontend/src/components/MachineSelectScreen.jsx`
   - `frontend/src/components/ResultScreen.jsx`
   - `backend/controllers/ui_api.py`
   - `backend/controllers/machine_control.py`
2. First change set target files:
   - `frontend/src/kiosk/hooks/useUiStatePolling.js`
   - `frontend/src/kiosk/KioskRouter.jsx`
   - `frontend/src/kiosk/adapters/uiStateAdapter.js`
   - minimal `App.jsx` refactor to use the above

### B) Exact dependencies to confirm before coding
- Confirm whether to keep zero new UI dependencies in initial parity pass.
- If dependencies are approved later, verify versions and bundling impact for:
  - `tailwindcss`
  - `framer-motion`
  - `lucide-react`
- Confirm no backend API key/auth flow changes are needed for UI work.

### C) Exact acceptance criteria before coding starts
- Design parity checklist approved against supplied demo + screenshots.
- Backend contract gap table approved (must-have vs optional fields).
- Phase-1 file plan approved (hook/router/adapter only, no behavior drift).
- Agreement that backend remains source of truth and JSX is preferred over TypeScript.

## Next implementation step after this planning update

Once this plan revision is approved, the immediate next implementation step is:

1. **Contract-first kickoff (no visual migration yet)**
   - Finalize where `input_mode` is configured (backend config source + API exposure path).
   - Confirm fallback behavior when mode is absent.
2. **Implement Phase 3 dual-mode foundation first**
   - Add adapter + interaction policy layer.
   - Wire router to pass mode-aware capabilities to screens.
3. **Only then begin Phase 4 screen migration**
   - Build each new screen with dual-mode behavior from initial implementation, avoiding later retrofits.
