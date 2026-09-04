# Documentation Hub

This is the documentation operating system for the repository.

## Purpose
Provide one predictable structure for:
- current system understanding,
- completed implementation history,
- future/backlog planning,
- historical/archive references,
- Codex-safe navigation before code changes.

## Top-level map
- [`CODEX_GUIDE.md`](./CODEX_GUIDE.md) — read-first workflow for Codex and contributors.
- [`architecture/`](./architecture/README.md) — current architecture and system-level references.
- [`operations/`](./operations/README.md) — runbooks, diagnostics, and deployment/ops references.
- [`integrations/`](./integrations/README.md) — integration-specific docs (including Reisa).
- [`reference/`](./reference/settings-catalog.md) — canonical configuration/reference docs.
- [`ai/`](./ai/README.md) — AI-oriented quick-orientation layer.
- [`project/`](./project/README.md) — project-wide backlog and historical project notes.
- [`CURRENT_STATE.md`](./CURRENT_STATE.md) — verified snapshot of what actually runs today, and what is not implemented.
- [`admin-guides/`](./admin-guides/README.md) — **source** of the protected Help Hub in `/dev/admin`; the README is the authoring guide.
- [`public-help/`](./public-help/) — source of the unauthenticated `/help` page, bundled into the frontend.
- [`../AGENTS.md`](../AGENTS.md) — repository-wide operating rules for AI agents (tool-neutral).

## Phase 1 foundation docs (current canonical)
- Operations:
  - [`operations/runbooks/install-and-bootstrap.md`](./operations/runbooks/install-and-bootstrap.md)
  - [`operations/runbooks/kiosk-and-e2e-testing.md`](./operations/runbooks/kiosk-and-e2e-testing.md) — Pi kiosk, API key, Shelly / full-stack Reisa
  - [`operations/runbooks/update-and-upgrade.md`](./operations/runbooks/update-and-upgrade.md)
  - [`operations/runbooks/recovery-and-rollback.md`](./operations/runbooks/recovery-and-rollback.md)
  - [`operations/runbooks/troubleshooting-matrix.md`](./operations/runbooks/troubleshooting-matrix.md)
- Architecture:
  - [`architecture/runtime-lifecycle.md`](./architecture/runtime-lifecycle.md)
- Reference:
  - [`reference/settings-catalog.md`](./reference/settings-catalog.md)
- Reisa operations:
  - [`integrations/reisa/runbooks/reisa-operator-playbook.md`](./integrations/reisa/runbooks/reisa-operator-playbook.md)
- AI orientation:
  - [`ai/README.md`](./ai/README.md)
  - [`ai/system-quick-map.md`](./ai/system-quick-map.md)

- Phase 2 core references:
  - [`reference/api-reference.md`](./reference/api-reference.md)
  - [`reference/database-schema-and-lifecycle.md`](./reference/database-schema-and-lifecycle.md)
  - [`reference/scripts-and-tools.md`](./reference/scripts-and-tools.md)
  - [`architecture/hardware-topology-and-telemetry.md`](./architecture/hardware-topology-and-telemetry.md)
  - [`architecture/ui-state-contract.md`](./architecture/ui-state-contract.md)
  - [`operations/runbooks/runtime-and-process-management.md`](./operations/runbooks/runtime-and-process-management.md)
  - [`operations/runbooks/auth-and-admin-access.md`](./operations/runbooks/auth-and-admin-access.md)
  - [`operations/runbooks/kiosk-and-e2e-testing.md`](./operations/runbooks/kiosk-and-e2e-testing.md)

## Documentation conventions

### 1) Where completed work docs go
- For subsystem/integration phase execution notes: place under that subsystem’s `completed/` area.
  - Example: `docs/integrations/reisa/completed/phases/phase-XX-execution-note.md`.

### 2) Where future ideas go
- Put actionable, not-yet-done items in that subsystem’s `future/README.md`.
- Cross-cutting/project-wide non-subsystem items go in `docs/project/future/backlog.md`.

### 3) Where archive/history goes
- Superseded plans, snapshots, and raw references go under an `archive/` area within the relevant subsystem/domain.
- Keep archive docs accessible, but do not treat them as current source-of-truth.

### 4) Subsystem naming conventions
- Use stable folders by codebase domain (e.g., `integrations/reisa`, `operations`, `architecture`).
- Prefer descriptive kebab-case file names.
- For phase notes, use `phase-XX[-Y]-execution-note.md` for sortable chronology.

### 5) Codex navigation expectations
Before implementing changes:
1. Read [`docs/CODEX_GUIDE.md`](./CODEX_GUIDE.md).
2. Read relevant subsystem `README.md`.
3. Read subsystem `completed` summary, then `future` backlog.
4. Open archive docs only when historical rationale is needed.

## Help Hub content
`docs/admin-guides/` and `docs/public-help/` are **compiled source**, not prose. They are
built into JSON manifests by `python -m backend.help.cli`, and a defect in a guide fails
the build rather than reaching an operator. Do not edit a guide without reading
[`admin-guides/README.md`](./admin-guides/README.md), and do not treat a guide as a place
to restate a runbook — the corpus is derived from the runbooks for a different reader
(an operator at the kiosk with only the admin panel), not mirrored from them.

## Current source-of-truth rule
- **Current behavior:** repo root `README.md` + [`CURRENT_STATE.md`](./CURRENT_STATE.md) +
  domain summaries in `docs/`.
- **Historical detail:** execution notes and archive docs.
- When a doc and the code disagree, the code wins and the doc gets fixed in the same change.

## Documentation maintenance rules
- When moving/renaming docs, update links in the same change.
- Keep one canonical location per topic (link to it instead of duplicating content).
- Preserve historical phase/archive files; add context with index docs rather than rewriting history.
- Before merging doc restructures, run a quick link check across `docs/**/*.md` and `README.md`.
