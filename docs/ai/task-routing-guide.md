# AI Task Routing Guide

Use this guide to minimize hallucination and route tasks to the right files quickly.

## Core rule
Read docs first, then verify behavior in code before answering.

## Task routing table

## Install/bootstrap task
Read first:
- `docs/operations/runbooks/install-and-bootstrap.md`
- `docs/operations/runbooks/runtime-and-process-management.md`

Then verify in code:
- `backend/app.py`
- `backend/setup/seed_settings.py`
- `backend/setup/seed_machines.py`

## Update/rollback task
Read first:
- `docs/operations/runbooks/update-and-upgrade.md`
- `docs/operations/runbooks/recovery-and-rollback.md`

Then verify in code:
- entrypoints and bootstrap files
- any changed module in diff

## API behavior question
Read first:
- `docs/reference/api-reference.md`

Then verify in code:
- `backend/flask_server.py`
- `backend/controllers/ui_api.py`

## Auth/admin access question
Read first:
- `docs/operations/runbooks/auth-and-admin-access.md`
- `docs/reference/settings-catalog.md`

Then verify in code:
- `backend/flask_server.py`
- `backend/controllers/ui_api.py`
- `backend/models/setting_model.py`

## Hardware/scanner issue
Read first:
- `docs/operations/runbooks/hardware-and-scanner-troubleshooting.md`
- `docs/architecture/hardware-topology-and-telemetry.md`

Then verify in code:
- `backend/controllers/qr_scanner.py`
- `backend/controllers/telemetry.py`
- `backend/utils/shelly_control.py`

## Frontend/backend state mismatch
Read first:
- `docs/architecture/ui-state-contract.md`

Then verify in code:
- `frontend/src/App.jsx`
- `frontend/src/api/backend.js`
- `backend/controllers/machine_control.py`
- `backend/controllers/ui_api.py`

## Reisa diagnostics/replay task
Read first:
- `docs/integrations/reisa/runbooks/reisa-operator-playbook.md`
- `docs/reference/api-reference.md` (admin reisa routes)

Then verify in code:
- `backend/services/reisa_audit_service.py`
- `backend/services/reisa_retry_service.py`
- `backend/services/reisa_replay_service.py`
- `backend/providers/reisa_provider.py`

## Database/schema question
Read first:
- `docs/reference/database-schema-and-lifecycle.md`

Then verify in code:
- `backend/models/*.py`
- relevant service files for lifecycle transitions

## Scripts/tooling question
Read first:
- `docs/reference/scripts-and-tools.md`

Then verify in code:
- script files directly (`run-*.sh`, `frontend/scripts/*`, `tools/*`, `Testing_Files/*`)

## If docs and code conflict
Required output behavior:
1. State conflict explicitly.
2. Prefer code as source of truth.
3. Recommend doc update path.

## Unknown / requires verification from code usage
When a requested fact is not directly shown in inspected files, answer with:
`Unknown / requires verification from code.`
