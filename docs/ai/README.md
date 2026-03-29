# AI Documentation Layer

## What this layer is for
This folder gives AI assistants a **high-signal orientation path** for this repository.

Goal: minimize hallucination and speed up accurate answers by directing the AI to canonical docs and critical code files.

---

## Best read order for AI
1. Repo overview: [`../../README.md`](../../README.md)
2. Docs hub: [`../README.md`](../README.md)
3. Runtime internals: [`../architecture/runtime-lifecycle.md`](../architecture/runtime-lifecycle.md)
4. System quick map: [`./system-quick-map.md`](./system-quick-map.md)
5. Install/update/rollback runbooks under `docs/operations/runbooks/`
6. Settings catalog: [`../reference/settings-catalog.md`](../reference/settings-catalog.md)
7. Reisa playbook (if integration-related): [`../integrations/reisa/runbooks/reisa-operator-playbook.md`](../integrations/reisa/runbooks/reisa-operator-playbook.md)

---

## Source-of-truth map

### Canonical docs
- Install/bootstrap: `docs/operations/runbooks/install-and-bootstrap.md`
- Update/upgrade: `docs/operations/runbooks/update-and-upgrade.md`
- Recovery/rollback: `docs/operations/runbooks/recovery-and-rollback.md`
- Runtime lifecycle: `docs/architecture/runtime-lifecycle.md`
- Settings catalog: `docs/reference/settings-catalog.md`
- Reisa operations: `docs/integrations/reisa/runbooks/reisa-operator-playbook.md`
- Incident triage table: `docs/operations/runbooks/troubleshooting-matrix.md`

### Historical context (not primary source)
- `docs/integrations/reisa/completed/phases/*`
- `docs/**/archive/*`

---

## AI orientation rules before answering
1. Identify task type first: install, runtime bug, auth, hardware, Reisa, frontend, DB, test.
2. Read canonical runbook/reference doc for that domain before reading deep code.
3. Confirm whether answer needs current behavior from code (e.g., route names, settings keys).
4. Prefer concrete command examples already documented.
5. If docs and code disagree, report drift explicitly and cite both.

---

## Where to look first by topic
- Install/bootstrap: `docs/operations/runbooks/install-and-bootstrap.md`
- Update/release safety: `docs/operations/runbooks/update-and-upgrade.md`
- Recovery/rollback: `docs/operations/runbooks/recovery-and-rollback.md`
- Runtime order/threads: `docs/architecture/runtime-lifecycle.md`
- Settings/env: `docs/reference/settings-catalog.md`
- Reisa: `docs/integrations/reisa/runbooks/reisa-operator-playbook.md`
- Troubleshooting: `docs/operations/runbooks/troubleshooting-matrix.md`
- API/admin command examples: `docs/operations/runbooks/admin-command-examples.md`
- Tests: `backend/tests/`

---

## High-risk areas AI should treat carefully
- Startup side effects across `backend/app.py` and `backend/flask_server.py`
- Machine state + timer interactions in `backend/controllers/machine_control.py`
- Telemetry threshold transitions in `backend/controllers/telemetry.py`
- Reisa replay/retry state repair (`backend/services/reisa_replay_service.py`)
- Settings changes affecting auth/provider/hardware behavior

---

## Operational safety posture for AI suggestions
- Prefer non-destructive checks first.
- Require explicit warning before DB-destructive actions.
- Recommend DB backup before upgrade/rollback or risky recovery actions.
- Avoid suggesting blind retry/replay loops for Reisa jobs.
