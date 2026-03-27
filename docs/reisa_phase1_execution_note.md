# Reisa Phase 1 Execution Note

## Files changed
- `backend/services/start_orchestrator.py` (new)
- `backend/services/__init__.py` (new)
- `backend/controllers/ui_api.py`
- `backend/controllers/qr_scanner.py`

## What was moved / extracted / wrapped
- Added a new orchestration entrypoint module (`start_orchestrator`) for start-flow ingress.
- Extracted route/scanner orchestration call-shape out of controller endpoints by wrapping existing `machine_control` functions instead of rewriting underlying behavior.
- Updated `/api/scan_code` path to delegate through `ingest_scan(...)`.
- Updated `/api/start_machine` path to delegate through `start_from_code(...)`.
- Updated `/api/i4_event` path to delegate through `start_from_button(...)`.
- Updated scanner callback path (`qr_scanner._handle_scanned_value`) to delegate through `ingest_scan(...)`.

## Behavior expected to remain unchanged
- Local code validation remains implemented by `machine_control.validate_code(...)` and local DB models.
- Machine start initiation still uses `machine_control.start_machine(...)` and existing Shelly control path.
- Usage decrement timing remains telemetry-confirmed through existing `machine_control` pending-start + `runstate_started` listener flow.
- Existing UI state transitions still come from `machine_control` state management.
- Route contracts/endpoints are unchanged (`/api/scan_code`, `/api/start_machine`, `/api/i4_event`, `/api/ui_state`).

## Remaining risks
- `machine_control.py` still holds dense orchestration/state logic (intentional for this phase to avoid risky behavior changes).
- Telemetry callback finalization is still implemented directly in `machine_control`, not yet promoted to dedicated orchestrator/session service.
- Global in-memory state (`UI_STATE`, pending starts, armed code) remains a coupling and durability risk across process restarts.
- Mixed DB session usage across modules remains unchanged.

## Recommended Phase 2 next
- Introduce provider abstraction for **local mode only** (e.g., `providers/base_provider.py` + `providers/local_provider.py`) and route validation/commit paths through it without changing business behavior.
- Add a thin usage/session service boundary to start isolating commit/idempotency semantics from `machine_control` internals.
- Keep telemetry-confirmed commit timing identical while moving commit call-site behind provider/service interface.

## Phase 1 completion update

### Additional files changed
- `backend/controllers/machine_control.py`
- `backend/services/start_orchestrator.py`

### Newly extracted or rerouted
- Added orchestrator-owned confirmed-start entrypoint: `start_orchestrator.handle_start_confirmed(machine_id)`.
- Rerouted telemetry `runstate_started` callback path so `machine_control._on_runstate_started(...)` now delegates to orchestrator instead of finalizing the full success flow inline.
- Added low-level helper boundaries in `machine_control` for orchestrator use:
  - `consume_pending_start(machine_id)` to consume pending-start runtime state.
  - `finalize_successful_start(machine_id, code_info)` as a compatibility wrapper around existing success finalization internals.

### What intentionally remains in `machine_control.py`
- Local code validation and local usage debit internals remain in `machine_control` for Phase 1 safety.
- Runtime/hardware concerns remain there (machine availability lookup, relay dispatch, button arming/disarming, UI state mutation helpers, telemetry store interactions).
- Existing in-memory state containers (`_pending_starts`, `_armed_code`, `UI_STATE`) remain unchanged in design.

### Behavior expected to remain unchanged
- Scan ingress, API start, and i4 button start still preserve previous route contracts and local logic outcomes.
- Usage decrement is still performed only after telemetry confirms machine start (confirmed-start path now routed through orchestrator).
- UI messages/state transitions and local DB usage behavior remain as before.

### Recommended Phase 2 next
- Introduce a local-only provider abstraction (`base_provider` + `local_provider`) and move local entitlement/commit interfaces behind it without changing start-confirmed timing.
- Begin extracting commit/idempotency semantics into a dedicated service while retaining current UI/runtime behavior.
