# Documentation Governance

This file defines how docs stay aligned with code.

## Scope
Applies to repository root docs and all `docs/**` content.

## Source-of-truth policy
- Code is source of truth for runtime behavior.
- Reference docs are source of truth for operator procedures only when validated against code.
- Archive docs are historical context and must not be used as canonical behavior.

## Mandatory doc update triggers
Update docs in the same change when you modify:

## API surface changes
If routes, auth wrappers, status semantics, or payload fields change:
- update `docs/reference/api-reference.md`
- update impacted runbooks/examples

## Settings changes
If adding/removing/changing settings keys or semantics:
- update `docs/reference/settings-catalog.md`
- update relevant runbooks

## Model/schema/lifecycle changes
If adding/changing model columns or lifecycle transitions:
- update `docs/reference/database-schema-and-lifecycle.md`
- update troubleshooting/recovery docs when impact exists

## Startup/runtime behavior changes
If entrypoint behavior, worker startup, or process ownership changes:
- update `docs/architecture/runtime-lifecycle.md`
- update `docs/operations/runbooks/runtime-and-process-management.md`

## Hardware/telemetry changes
If device roles, metric source logic, threshold behavior, or relay flow changes:
- update `docs/architecture/hardware-topology-and-telemetry.md`
- update hardware troubleshooting runbook

## Script/tooling changes
If launchers/tools change:
- update `docs/reference/scripts-and-tools.md`
- update install/update docs if command paths change

## Drift detection checklist
Run these checks before merging doc-sensitive changes:

```bash
# Route inventory
python - <<'PY'
from backend.flask_server import app
for r in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    if r.endpoint != 'static':
        print(','.join(sorted(r.methods-{'HEAD','OPTIONS'})), r.rule)
PY

# Settings keys in code
rg "get_setting_value\(|update_setting_value\(" backend -n

# Script inventory
rg --files run-*.sh backend/scripts backend/setup frontend/scripts tools Testing_Files
```

## Ownership expectations
- Every code PR author is responsible for doc updates caused by their changes.
- Reviewers should block merge on obvious code-doc contradictions.
- Operational runbooks must be reviewed for command validity after major runtime changes.

## Archive rules
- Keep historical docs under explicit `archive/` paths.
- Do not silently repurpose archive docs as current instructions.
- If an old doc is superseded, add a link to canonical replacement.

## Required contradiction handling
When docs and code disagree:
1. mark discrepancy explicitly in PR notes or docs issue list,
2. update docs to match current code,
3. if code is wrong and docs represent intended behavior, state that docs are aspirational until code is fixed.

## Unknown / requires verification from code
- No automated docs linter currently enforces this policy; compliance is process-driven.
