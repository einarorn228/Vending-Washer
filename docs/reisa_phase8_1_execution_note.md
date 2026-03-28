# Reisa Phase 8.1 Execution Note

## Files changed
- `backend/integrations/reisa_contract.py`
- `backend/setup/seed_settings.py`
- `backend/tests/test_reisa_hardening.py`
- `docs/reisa_phase7_execution_note.md`
- `docs/reisa_phase8_1_execution_note.md` (new)

## Default contract value corrected
- Updated default Reisa completion action from:
  - `WASHING_MACHINE_COMPLETED`
- To:
  - `WASHING_MACHINE_COMPLETE`

This aligns the default with the documented Reisa API status action example.

## Configurability confirmation
- Completion action remains configurable through settings via `reisa_action_completion`.
- The seeded/default value now uses `WASHING_MACHINE_COMPLETE`.

## Remaining caveats
- Existing deployments that already persisted `reisa_action_completion` in the DB will keep their current stored value until updated.
- The change only corrects defaults and documentation alignment; runtime override behavior is unchanged.
