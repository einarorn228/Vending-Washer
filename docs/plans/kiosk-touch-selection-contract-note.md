# Kiosk touch-selection contract note (pre full-screen migration)

> **Status note (updated May 15, 2026):** This plan/note contains historical references to the older dual-mode model. Current behavior is touch-first with optional button-box input via `button_box_enabled`; `kiosk_input_mode`/`input_mode` are legacy compatibility metadata only. See `docs/reference/api-reference.md`, `docs/reference/settings-catalog.md`, and `docs/architecture/ui-state-contract.md` for the current contract.


## Purpose
This note reviews the **current** backend/frontend contract for machine selection/start and defines the smallest safe contract for touch-mode selection while preserving backend authority.

---

## 1) Current touch-selection feasibility

### Short answer
**Not fully feasible today for safe touch-mode selection from the frontend.**

### Why
- Backend currently supports these action endpoints:
  - `POST /api/scan_code` (ingest scan)
  - `POST /api/start_machine` (start by `machine_id` + `code`)
  - `POST|GET /api/i4_event` (hardware button index path)
- `GET /api/ui_state` includes backend state and `input_mode`, but does **not** expose a frontend-safe selection token/session handle that can be used instead of raw code.
- Current frontend API client only calls `GET /api/ui_state` (`frontend/src/api/backend.js`) and has no start/select action call path yet.
- Existing `start_machine` contract requires raw code (`code`) + `machine_id`, which would require exposing/supplying raw code in frontend touch flow.

### What *is* already possible with current payloads
Touch-mode UI can already do **read-only** mode-aware rendering safely:
- Use `input_mode` from `/api/ui_state` (already normalized on backend).
- Use backend `state`, `message`, and `machines` as source of truth for screen content.

But **initiating selection/start from touch** without exposing code is not currently supported by contract.

---

## 2) Current action path analysis

### Scan ingestion path today
1. Scanner/API sends code to `ingest_scan(...)` (`backend/services/start_orchestrator.py`).
2. On success, backend arms code/session and sets `UI_STATE` to:
   - `state = choose_machine`
   - `message = SELECT_MACHINE_MESSAGE`
   - `machines = telemetry snapshot`
   - `uses_left`
   - `current_machine = None`
3. Frontend polls `/api/ui_state` and renders based on that state.

### Machine start from code path today
- Endpoint: `POST /api/start_machine`
- Required request data today:
  - `machine_id`
  - `code`
- Backend call chain:
  - `ui_api.start_machine_endpoint` -> `start_from_code(machine_id, raw_code)` -> provider lookup/authorize -> `start_machine(...)`.

### Machine start from hardware button path today
- Endpoint: `POST|GET /api/i4_event` with `button` index.
- Backend call chain:
  - `ui_api.i4_event` -> `start_from_button(index)` -> resolve machine by button -> consume armed/pending scan context server-side -> authorize/start.
- This flow does **not** require frontend to know raw code.

### What data is required to start today?
- For `/start_machine`: raw `code` + `machine_id`.
- For `/i4_event`: `button` only; backend resolves machine and uses armed scan state.

### Where does required data live?
- Armed/pending scan session context is backend-owned (`machine_control` + `start_orchestrator` state/session services).
- Raw code exists at scan ingress and is tracked server-side for authorization/commit lifecycle.
- Machine availability snapshot is backend-owned via telemetry store.

### Does frontend currently have access to required start data?
- Frontend has `machine_id` via `ui_state.machines`.
- Frontend does **not** receive raw code from `ui_state` (good).
- Frontend currently has no API helper for scan/start actions in kiosk router flow.

### Should frontend have access to raw code?
- **Prefer no.**
- Keeping raw code out of frontend aligns with backend source-of-truth, reduces accidental leakage, and avoids coupling UI actions to provider auth internals.

---

## 3) Recommended safest contract

## Recommendation (smallest safe change)
Add a backend endpoint that starts/selects machine using **backend-held armed session context**, not raw code from frontend.

### Proposed endpoint
`POST /api/touch_select_machine`

### Request shape
```json
{
  "machine_id": "washer_1"
}
```

### Response shape
Success example:
```json
{
  "success": true,
  "message": "<backend start message>",
  "uses_left": 2,
  "state": "machine_starting"
}
```

Failure example:
```json
{
  "success": false,
  "message": "No valid scan in progress.",
  "state": "choose_machine"
}
```

### Expected preconditions
- Current `ui_state.state == "choose_machine"`.
- Backend has an armed/pending valid scan/session context.
- `machine_id` exists and is currently available.
- (Policy gate) `input_mode == "touch"` (or equivalent backend interaction policy allowing touch select).

### Expected failure cases
- Missing/invalid `machine_id` -> `400`.
- No valid armed scan context -> `409` with explicit message.
- Invalid/expired authorization at start time -> `409`.
- Machine unavailable/busy -> `409`.
- Wrong state (not `choose_machine`) -> `409` (busy or invalid state).
- Touch disabled by config/policy -> `409` or `403` (prefer explicit policy message).

### Why this is safest
- Keeps backend as sole authority for current scan/session validity.
- Avoids exposing raw code to frontend.
- Reuses existing backend start path semantics (same `start_machine` outcomes/state transitions).
- Small, reviewable contract extension (single endpoint, no screen migration coupling).

### Optional payload addition (nice-to-have, not required for first contract step)
- Add `selection_context` in `/api/ui_state` for UX hints (e.g., `active_machine_id`), primarily for hardware highlight parity.
- Not required to unblock touch start request contract.

---

## 4) Hardware-button compatibility

The proposed touch endpoint does **not** break current hardware flow because:
- `POST /api/i4_event` remains unchanged for physical buttons.
- Existing scanner -> choose_machine -> button start orchestration remains intact.
- Touch contract is additive and can be gated by `input_mode` / policy checks.
- Backend state machine (`waiting_for_code` -> `choose_machine` -> `machine_starting`/`machine_in_use`) remains authoritative for both paths.

---

## 5) Migration recommendation

### Exact next implementation step
**Implement a small backend contract step first** (before full screen migration):
1. Add `POST /api/touch_select_machine` that starts from backend-held armed scan/session (no raw code in request).
2. Enforce state and mode preconditions (`choose_machine`, touch-allowed).
3. Return concise success/failure payload aligned with existing API style.
4. Add focused backend tests for preconditions/failure cases.

After this small backend contract is merged, proceed with full screen migration and wire touch UI interactions to this endpoint.

---

## Conclusion
Current backend/frontend contract is ready for dual-mode **rendering**, but not yet ready for safe touch machine selection/start without exposing raw code. A minimal additive backend endpoint is the safest next step and preserves hardware-button compatibility.
