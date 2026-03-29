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
- [`project/`](./project/README.md) — project-wide backlog and historical project notes.

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

## Current source-of-truth rule
- **Current behavior:** repo root `README.md` + domain summaries in `docs/`.
- **Historical detail:** execution notes and archive docs.

## Documentation maintenance rules
- When moving/renaming docs, update links in the same change.
- Keep one canonical location per topic (link to it instead of duplicating content).
- Preserve historical phase/archive files; add context with index docs rather than rewriting history.
- Before merging doc restructures, run a quick link check across `docs/**/*.md` and `README.md`.
