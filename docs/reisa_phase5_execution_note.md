# Reisa Phase 5 Execution Note

## Files changed
- `backend/integrations/__init__.py` (new)
- `backend/integrations/reisa_client.py` (new)
- `backend/integrations/reisa_service.py` (new)
- `backend/providers/reisa_provider.py` (new)
- `backend/providers/provider_selector.py` (new)
- `backend/providers/__init__.py`
- `backend/services/start_orchestrator.py`
- `backend/setup/seed_settings.py`
- `docs/reisa_phase5_execution_note.md` (new)

## What read-only Reisa pieces were added
- Added a dedicated `ReisaClient` for read-only HTTP operations with bearer auth, timeout controls, and normalized error handling for:
  - `GET /info`
  - `GET /uuid/{uuid}`
  - `GET /pin/{pin}`
- Added `ReisaService` to normalize Reisa response payloads into a consistent `ReisaEntitlement` shape used by providers/orchestration.
- Added `ReisaProvider` implementing provider contract methods for:
  - real lookup (`lookup`)
  - real authorization (`authorize`) based on remaining quantity (`totalQuantity - usedQuantity`)
  - safe read-only commit/completion stubs (no external writes)

## How provider selection currently works
- Added a small provider resolver (`provider_selector.resolve_provider`) that reads DB settings.
- Default remains **local**.
- Reisa activates only when both are true:
  - `provider_default = reisa`
  - `provider_reisa_enabled = true`
- Added seed defaults for:
  - `provider_default`
  - `provider_reisa_enabled`
  - `reisa_base_url`
  - `reisa_bearer_token`
  - `reisa_connect_timeout_ms`
  - `reisa_read_timeout_ms`

## What Reisa operations are supported in this phase
- Read-only entitlement lookup and shaping:
  - by UUID
  - by PIN
  - auto lookup mode (UUID-first fallback to PIN)
- Authorization using normalized remaining quantity.
- Reisa path is now available via orchestrator provider-selection boundaries.

## What Reisa operations are intentionally NOT implemented yet
- No usage deduction (`POST /uuid/{uuid}/deduct`).
- No status posting (`POST /uuid/{uuid}/status`).
- No metadata posting (`POST /uuid/{uuid}/metadata`).
- `commit_start()` and `mark_completion()` in `ReisaProvider` are explicit read-only deferrals/no-op-success behavior for safety in this phase.

## What behavior should remain unchanged
- Local provider remains default and retains existing behavior.
- Machine control, relay switching, telemetry confirmation, and UI state ownership remain local.
- Usage-session lifecycle persistence remains in local DB and still tracks start/commit/completion transitions.

## Risks that remain
- Reisa commit/completion are intentionally deferred; usage accounting authority is still local for committed starts.
- Reisa auto lookup mode uses UUID-first heuristics; malformed identifiers can still rely on PIN fallback behavior.
- Runtime provider selection currently reads settings at call time; inconsistent setting updates during active sessions can change provider routing between steps.

## Ready for first Reisa write/commit phase later?
- **Yes.**
- The code now has a clean read-only Reisa path and provider seam without introducing external write side effects.
- Next phase can add idempotent Reisa commit/start deduction against existing usage-session lifecycle checkpoints.
