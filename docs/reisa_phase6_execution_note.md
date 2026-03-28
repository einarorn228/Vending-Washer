# Reisa Phase 6 Execution Note

## Files changed
- `backend/integrations/reisa_client.py`
- `backend/integrations/reisa_service.py`
- `backend/providers/reisa_provider.py`
- `backend/providers/provider_selector.py`
- `backend/services/usage_session_service.py`
- `backend/services/start_orchestrator.py`
- `docs/reisa_phase6_execution_note.md` (new)

## What Reisa write operations were added
- Added Reisa client write methods:
  - `POST /uuid/{uuid}/status` via `ReisaClient.post_status(...)`
  - `POST /uuid/{uuid}/deduct` via `ReisaClient.post_deduct(...)`
- Added Reisa service wrappers:
  - `ReisaService.post_start_status(...)` with action `WASHING_MACHINE_START`
  - `ReisaService.deduct_usage(...)` returning normalized `uses_left` where available
- Implemented real `ReisaProvider.commit_start(...)`:
  1. post start status to Reisa
  2. deduct quantity `1`
  3. return remaining quantity when available (or fallback estimate)

## How provider consistency across session lifecycle is ensured
- Added provider resolution by persisted session provider identity using:
  - `resolve_provider_for_session(...)`
  - `resolve_provider_by_name(...)`
- Start flows now prefer provider identity from existing scanned-session linkage when present (`_provider_for_existing_scan`).
- Session-creation/linking now returns a stable provider selection with the session UID; if scanned-session provider differs from current settings, orchestration re-authorizes with the persisted provider before start.
- Confirmed-start commit now resolves provider from persisted usage-session provider (`UsageSession.provider`) instead of current global settings.

## How confirmed-start commit now works in Reisa mode
- Timing remains unchanged: commit logic still runs only in `handle_start_confirmed(...)` after telemetry `runstate_started`.
- Confirmed-start flow in Reisa mode now:
  1. consume pending start
  2. mark session `start_confirmed`
  3. resolve provider from session provider identity
  4. call `provider.commit_start(...)`
     - Reisa provider posts `WASHING_MACHINE_START`
     - Reisa provider deducts quantity `1`
  5. mark local session committed (`commit_ok`) and finalize UI/runtime success
- If Reisa write fails after confirmed local start, session is marked `failed` with commit error details; failure is logged and surfaced through existing error state path.

## What behavior should remain unchanged
- Local provider behavior is unchanged (lookup/authorize/commit remains local DB behavior).
- No Reisa writes occur before telemetry-confirmed start.
- No completion-status/metadata writes were added in this phase.
- Existing machine-control timing and UI state progression remain unchanged outside commit-path provider consistency hardening.

## What risks remain
- Reisa UUID source for writes currently relies on entitlement token mapping (`entitlement.token`) as planned; if upstream payload contracts differ, commit may fail with missing UUID/token.
- No dedicated external idempotency key is yet sent to Reisa; duplicate callback protection is still primarily local via pending-start consumption and session commit transition guarding.
- Completion/action-finish writes are still deferred to later phase.

## Ready for Reisa completion/status-finish work later?
- **Yes.**
- The first confirmed-start write path is now implemented with stable session-bound provider routing, and local lifecycle tracking captures commit successes/failures needed for next-phase completion/status-finish integration.
