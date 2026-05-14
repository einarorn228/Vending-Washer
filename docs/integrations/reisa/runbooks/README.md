# Reisa Runbooks

Operational runbooks for day-to-day Reisa support, triage, and recovery.

## Contents
- [`reisa-operator-playbook.md`](./reisa-operator-playbook.md) — primary operator guide for diagnostics, retry, and replay.
- Bootstrap Reisa + optional “full stack” (relay, telemetry, CORS, retry worker): run `python -m backend.setup.configure_reisa` from repo root (see `--full-stack` in module docstring). End-to-end Pi checklist: [`../../operations/runbooks/kiosk-and-e2e-testing.md`](../../operations/runbooks/kiosk-and-e2e-testing.md).

## Source-of-truth note
- Treat runbooks as current operational guidance.
- Treat `../completed/` and `../archive/` as historical/implementation context.
