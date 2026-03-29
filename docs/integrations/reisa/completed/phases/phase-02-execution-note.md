# Reisa Phase 2 Execution Note

## Files changed
- `backend/providers/base_provider.py` (new)
- `backend/providers/local_provider.py` (new)
- `backend/providers/__init__.py` (new)
- `backend/services/start_orchestrator.py`
- `backend/controllers/machine_control.py`

## What provider abstraction was introduced
- Added a minimal provider contract (`BaseProvider`) with concrete result dataclasses for:
  - `lookup(identifier, mode)`
  - `authorize(entitlement, machine_id)`
  - `commit_start(entitlement, quantity)`
  - `mark_completion(entitlement, machine_id)`
- The contract is intentionally small and maps to real washer flow stages in this codebase:
  scan/code lookup, pre-start authorization, telemetry-confirmed commit, and completion hook.

## What `LocalProvider` now owns
- Local code lookup and validity checks (existence, expiration, usage remaining).
- Local authorization re-check before start.
- Local usage commit (`current_usage` increment and expiration rollover) in `commit_start(...)`.
- `mark_completion(...)` is a deliberate local no-op success for now.

## What still intentionally remains outside the provider
- Machine availability/runtime ownership (`MachineStateStore`) and relay control.
- Pending-start lifecycle and telemetry listener wiring.
- UI state transitions and user-facing messages.
- Scan logging/metrics/event logging.
- Physical button arming/disarming and i4 routing.

These remain in `machine_control`/telemetry because Phase 2 focuses only on introducing entitlement authority boundaries without changing runtime/hardware behavior.

## What behavior should remain unchanged
- Local QR/code validation still uses the same DB-backed rules.
- Machine starts still route through existing machine-control runtime path.
- Usage commit still happens only after telemetry confirms machine start (`runstate_started`).
- Existing API route contracts and scanner ingress contracts are unchanged.
- Existing UI state progression remains the same.

## Risks that remain
- Button-path start (`handle_i4_button`) still performs local validation directly in `machine_control`; provider usage is currently strongest on orchestrator code-start and telemetry-confirmed commit paths.
- In-memory state (`_pending_starts`, `UI_STATE`, armed code) is still process-local.
- Mixed DB session patterns across modules remain unchanged.
- Provider commit failures after confirmed telemetry currently surface as generic start error UI (same conservative failure UX as current path).

## What should happen in Phase 3 next
1. Introduce usage/session model extraction so start attempts and commits have explicit local session records.
2. Route button-path entitlement checks fully through provider/orchestrator to remove remaining direct local validation calls.
3. Keep provider contract stable while preparing read-only external-provider lookup integration behind the same interface.
4. Add focused tests around provider commit idempotency boundaries before any external provider write operations.
