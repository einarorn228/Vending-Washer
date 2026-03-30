# AI Safe and Risky Operations

This guide defines guardrails for AI-assisted operations in this repository.

## Safe-first operating rules
1. Use non-destructive checks before destructive actions.
2. Verify with code and current docs before suggesting commands.
3. Backup `codes.db` before risky maintenance/recovery actions.
4. Change one high-risk setting at a time.

## High-risk operations (do not do blindly)

## Database-destructive actions
Examples:
- deleting `codes.db`
- bulk DELETE via admin endpoints
- ad hoc SQL updates on lifecycle tables

Required before action:
- backup command
- explicit operator warning about impact

## Reisa replay/retry bulk actions
Examples:
- repeated `POST /admin/reisa/retry_due`
- enabling retry worker in unstable state

Required before action:
- inspect session diagnostics and pending jobs
- confirm idempotency context and failure categories

## Auth credential changes
Examples:
- rotating API key
- changing admin hash/username

Required before action:
- staged verification plan
- prevent lockout by validating one credential path at a time

## Relay control changes
Examples:
- setting `backend_relay_enabled=true`
- changing device role/IP/channel mappings

Required before action:
- verify physical mapping and safety
- run controlled single-machine test

## Runtime mode changes
Examples:
- switching from `backend.app` to `backend.flask_server` entrypoint

Required before action:
- explicit warning that Flask-only path does not launch full worker set

## Medium-risk operations
- timeout tuning (`button_select_timeout_sec`, `selection_timeout_sec`)
- telemetry thresholds in `machine_configs`
- scanner serial settings

Required before action:
- baseline capture
- post-change health and flow verification

## Low-risk operations
- read-only diagnostics (`/api/ui_state`, `/admin/metrics`, log tailing)
- route/table inventory checks
- documentation updates

## Mandatory warnings AI should include
- Seed scripts are not migrations.
- Startup overlap exists between `backend/app.py` and `backend/flask_server.py`.
- Scanner settings require backend restart because serial config is import-time.
- Root launcher virtualenv assumptions are inconsistent (`run-backend.sh` vs docs).
- Frontend Pi launcher behavior is host-specific and currently launches Chromium twice.

## Required confirmation checklist before risky command suggestions
1. Is this destructive or externally side-effecting?
2. Is backup command provided?
3. Is rollback path documented?
4. Is auth/permission requirement clear?
5. Is expected success/failure output provided?

If any answer is no, do not provide the risky command as the first suggestion.

## Unknown / requires verification from code
- There is no built-in approval workflow in code for dangerous admin endpoints; operational discipline must enforce safeguards.
