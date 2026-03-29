# Reisa Integration Documentation

This folder is the canonical documentation hub for Reisa integration work in this repository.

## What this area is for
- Track what has already been implemented and executed across Reisa phases.
- Keep a curated, practical backlog of what is still valuable to test or improve.
- Preserve planning snapshots and historical references without mixing them into day-to-day reading.

## Quick status
- **Completed/executed work:** Phase 1 through Phase 10 (including Phase 2.5, 8.1, and 9.1 hardening updates) is documented under [`completed/`](./completed/README.md).
- **Future/not-yet-done ideas:** prioritized validation and improvement backlog is under [`future/`](./future/README.md).
- **History/reference material:** original planning snapshots and inventory artifacts are under [`archive/`](./archive/README.md).
- **Operator guidance:** practical triage/replay workflows are under [`runbooks/`](./runbooks/reisa-operator-playbook.md).

## Where to find what
- Implementation history by phase (detailed notes):
  - [`completed/phases/`](./completed/phases/)
- High-level completed summary:
  - [`completed/README.md`](./completed/README.md)
- Curated future backlog and priorities:
  - [`future/README.md`](./future/README.md)
- Planning snapshots and reference inventory:
  - [`archive/README.md`](./archive/README.md)
- Operator playbook:
  - [`runbooks/reisa-operator-playbook.md`](./runbooks/reisa-operator-playbook.md)

## Recommended reading order (human + Codex)
1. Start with [`CODEX_GUIDE.md`](./CODEX_GUIDE.md) for orientation and guardrails.
2. For incidents/day-2 operations, read [`runbooks/reisa-operator-playbook.md`](./runbooks/reisa-operator-playbook.md) first.
3. Read [`completed/README.md`](./completed/README.md) to understand what is already done.
4. Read [`future/README.md`](./future/README.md) to identify the right next increment.
5. Open only the needed phase execution notes under [`completed/phases/`](./completed/phases/) for implementation details.
6. Consult [`archive/`](./archive/) only when historical design rationale or old snapshots are needed.

## Documentation conventions
- New implementation-phase notes should go in `completed/phases/` using `phase-XX-execution-note.md` naming.
- New not-yet-implemented ideas should be added to `future/README.md` first (curated list), then split into dedicated docs only when large enough.
- Superseded plans/snapshots belong in `archive/` and should be linked from an index.
