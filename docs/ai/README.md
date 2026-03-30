# AI Documentation Layer

This folder is the AI orientation layer for accurate, code-grounded answers.

## Read order
1. `../../README.md`
2. `../README.md`
3. `../architecture/runtime-lifecycle.md`
4. `./system-quick-map.md`
5. `./task-routing-guide.md`
6. `./safe-and-risky-operations.md`
7. domain-specific runbooks/reference docs

## Canonical AI support docs
- [`system-quick-map.md`](./system-quick-map.md)
- [`task-routing-guide.md`](./task-routing-guide.md)
- [`safe-and-risky-operations.md`](./safe-and-risky-operations.md)

## Required AI behavior
- Treat code as source of truth.
- If docs and code conflict, call it out and prefer code.
- Use exact commands and payloads from repository docs/code.
- Mark uncertain points as `Unknown / requires verification from code.`
