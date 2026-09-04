# AGENTS.md — operating rules for AI agents in this repository

Tool-neutral. Every agent working here — Codex, ChatGPT, Claude, or anything else —
follows this file. `CLAUDE.md` stays the Claude Code project file and holds
Claude-specific commands and architecture notes; it does not replace these rules, and
these rules do not replace it.

This is a **live system**. A Raspberry Pi runs a kiosk that takes customers' money and
switches real washing machines on and off. A wrong assertion in a document, a stray
write to `codes.db`, or a relay flag flipped "just to test" has physical consequences
on someone's laundry and on the operator's afternoon. Work accordingly.

## 1. Verify against code before you assert

The single most common failure in this repository's history is a document that
confidently described behaviour the code never had. A setting named
`selection_timeout_sec` was documented in four places and has never existed.

- Read the source before writing a factual claim about it. Cite `file:line`.
- When a doc and the code disagree, **the code wins** and the doc gets fixed in the
  same change.
- Do not "improve" a document by making it more confident. Uncertainty stated plainly
  is worth more than a fluent guess.
- Do not copy a claim from another document as evidence. Documents here have been
  wrong; only the code and a command you actually ran are evidence.
- If you could not verify something, say **NOT VERIFIED** and say why. Never present
  an unrun command's expected output as a result.

## 2. Never touch these

- **`codes.db`** — the operator's live database: codes, settings, machine mapping,
  session history. Never write to it. Read it with
  `sqlite3 "file:codes.db?mode=ro" ...` if you must. Record its `sha256sum` before and
  after any task that goes near it.
- **`frontend/.env`** — contains the live `VITE_API_KEY`. Never read its values into a
  report, never rewrite it.
- **`backend_relay_enabled`** — never set it to `true`. That flag is the difference
  between a dry run and sending real commands to real relays.
- **The running kiosk stack on ports 3000 and 5000.** Do not restart it, do not bind to
  those ports, do not drive it with test traffic. If you need a running stack, copy the
  database to a scratch directory, point `VENDING_WASHER_DATABASE_URL` at the copy, and
  use spare ports.
- **`translation_status` on a Help guide** — never flip one to `published`. It is a
  statement that a human reviewed that translation's language. Making a check go green
  by changing it is falsifying a review.
- **Git history.** Do not force-push, rebase shared branches, or amend commits you did
  not write in this session.

## 3. Run the suites before claiming done

```bash
source .venv/bin/activate
python -m pytest backend/tests/ -q
python -m unittest discover -s backend/tests -t .
python -m compileall -q backend
python -m backend.help.cli --check          # only if you touched docs/admin-guides or docs/public-help
cd frontend && node --test src/dev-admin/help/ && npx vite build
```

Both Python runners are required: they exercise different collection paths and the
project has been broken under one while green under the other. `--check` must exit 0;
a `STALE:` line means a guide was edited without regenerating its manifest.

Tests are isolated from the live database by `backend/tests/_isolation.py`, which
redirects the engine through `VENDING_WASHER_DATABASE_URL`; `backend/models` refuses to
bind to `codes.db` under test. Do not weaken that guard.

Paste **real output**. "Tests pass" without output is not a claim this repository
accepts.

## 4. Keep the tree clean

- Branch before committing; never commit straight to `main`.
- Do not push and do not merge unless explicitly asked.
- Commit coherent units with a message that says what changed and why.
- Leave no stray scratch files, no `.md` reports written into the project tree, no
  commented-out code. Temporary work goes outside the repository.
- Do not reorganise the docs tree or move files as a side effect of another task.
- Do not add a second test toolchain, a formatter, or a dependency without being asked.

## 5. Scope discipline

Do exactly what was asked. If you find something else broken, **report it; do not fix
it** unless it blocks the task. An unrequested "while I was in there" change is the
hardest kind of diff to review and the easiest place for a regression to hide.

Two things in particular are explicitly out of bounds unless asked: process control
(there is no `restart_backend` action and no systemd unit — do not invent one), and any
endpoint that accepts a filesystem path.

## 6. Where the authoritative documents live

Point at these rather than restating them. If one of them is wrong, fix it there.

| Question | Document |
| --- | --- |
| What actually runs right now, and what is not implemented | [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) |
| Fast file routing by task type | [`docs/ai/system-quick-map.md`](docs/ai/system-quick-map.md) |
| What is safe vs risky to change | [`docs/ai/safe-and-risky-operations.md`](docs/ai/safe-and-risky-operations.md) |
| Kiosk UI state transitions and failure modes | [`docs/architecture/ui-state-contract.md`](docs/architecture/ui-state-contract.md) |
| Startup sequence, threads, bootstrap side effects | [`docs/architecture/runtime-lifecycle.md`](docs/architecture/runtime-lifecycle.md) |
| Hardware topology and telemetry behaviour | [`docs/architecture/hardware-topology-and-telemetry.md`](docs/architecture/hardware-topology-and-telemetry.md) |
| Every setting: default, type, range, risk | [`docs/reference/settings-catalog.md`](docs/reference/settings-catalog.md) |
| HTTP surface and auth per namespace | [`docs/reference/api-reference.md`](docs/reference/api-reference.md) |
| Tables, columns, and record lifecycle | [`docs/reference/database-schema-and-lifecycle.md`](docs/reference/database-schema-and-lifecycle.md) |
| Symptom → cause → fix | [`docs/operations/runbooks/troubleshooting-matrix.md`](docs/operations/runbooks/troubleshooting-matrix.md) |
| The `/dev/admin` panel, including the Help tab | [`docs/operations/runbooks/beta-dev-admin-panel.md`](docs/operations/runbooks/beta-dev-admin-panel.md) |
| Writing or fixing a Help guide | [`docs/admin-guides/README.md`](docs/admin-guides/README.md) |
| Reisa incidents, retries, replay | [`docs/integrations/reisa/runbooks/reisa-operator-playbook.md`](docs/integrations/reisa/runbooks/reisa-operator-playbook.md) |
| Doc conventions and where new docs go | [`docs/README.md`](docs/README.md) |

Anything under an `archive/` directory is a historical record. Read it for rationale;
never cite it as current behaviour, and do not rewrite it to match today.

## 7. Two rules specific to this codebase

**Route through the orchestrator.** All scan and start flows go through
`backend/services/start_orchestrator.py`. Do not call `machine_control` primitives
directly from a route.

**The frontend computes no state.** It polls `/api/ui_state` and renders what the
backend reports. A fix that adds state derivation to the frontend is the wrong fix.
