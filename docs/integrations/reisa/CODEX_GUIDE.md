# Codex Guide: Reisa Docs Navigation

Use this file as the first stop before changing Reisa-related code.

## Read this first (required order)
1. [`runbooks/reisa-operator-playbook.md`](./runbooks/reisa-operator-playbook.md) (for current operations/triage)
2. [`completed/README.md`](./completed/README.md)
3. [`future/README.md`](./future/README.md)
4. Only then open specific execution notes in [`completed/phases/`](./completed/phases/)

## Where completed work is documented
- Summary: [`completed/README.md`](./completed/README.md)
- Detailed per-phase history: [`completed/phases/`](./completed/phases/)

## Where future ideas are documented
- Curated backlog and priorities: [`future/README.md`](./future/README.md)

## Guardrail for future Codex tasks
- Do **not** re-implement already completed phases unless the task explicitly asks for refactor/fix on that phase.
- Before proposing new changes, map your task to:
  - already completed behavior (to avoid duplicates), and
  - backlog category (to keep increments intentional).
- Use `archive/` only for historical context, not as the default source of truth.
