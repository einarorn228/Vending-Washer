# Beta Dev/Admin Panel Runbook

## Purpose

The `/dev/admin` page is a temporary beta/dev control panel for trusted local deployments of the vending washer kiosk. It exists so beta operators can tune whitelisted settings and machine-card layout without SSH, VPN, command-line scripts, or manual database edits for every small change.

This is **not** the final production admin system.

## Access route

Frontend route:

```text
/dev/admin
```

Backend API namespace:

```text
/api/dev_admin/*
```

## Backend kill switch

The beta panel is controlled by the database setting:

```text
dev_admin_enabled
```

Default:

```text
false
```

When `dev_admin_enabled=false`, all `/api/dev_admin/*` endpoints return `403` and the frontend shows a disabled state.

### Enable the panel

Run from the repository root on the kiosk host:

```bash
source .venv/bin/activate
python - <<'PY'
from backend.models import Session
from backend.models.setting_model import update_setting_value

session = Session()
try:
    update_setting_value(session, "dev_admin_enabled", "true")
finally:
    session.close()
PY
```

### Disable the panel

```bash
source .venv/bin/activate
python - <<'PY'
from backend.models import Session
from backend.models.setting_model import update_setting_value

session = Session()
try:
    update_setting_value(session, "dev_admin_enabled", "false")
finally:
    session.close()
PY
```

Disable the panel when not actively using it.

## Temporary lock/password

The page starts locked. The temporary password is the same value as the kiosk API key.

This is only a beta guard:

- the API key may be bundled into frontend JavaScript if `VITE_API_KEY` is used,
- the API key may be readable from browser devtools if stored in `localStorage.API_KEY`,
- anyone with the admin credentials can unlock this panel while `dev_admin_enabled=true`,
- there are no users, roles, OAuth, rate limits, or production-grade account controls.

There *is* a configuration audit trail (see **Change history** below), but it records what changed, not who changed it — there is only one admin account.

Do not expose `/dev/admin` or `/api/dev_admin/*` to the public internet.

## Secrets policy for first beta

Raw secrets are never displayed. `api_key`, `admin_password_hash`, and `reisa_bearer_token`
show only `Set / masked` or `Not set`.

Two secrets can be **rotated** (never read) from the Sensitive Settings section, and both
require re-entering the current API key as proof of identity:

- `api_key` — via **Generate New API Key**. The new value is shown once, in a modal. Write it
  down: every kiosk still using the old key loses access immediately, and you will need the new
  value for `VITE_API_KEY` / `localStorage.API_KEY`.
- `reisa_bearer_token` — via **Update Reisa Token**.

Both rotations are recorded in the audit log by presence only (`<set>` / `<not set>`), never by
value. `admin_password_hash` remains read-only.

## Config export and backup before risky changes

Use **Export current config** in the Overview page before changing risky settings or Advanced / Technical Mapping fields. The export excludes raw secrets and includes only secret `is_set` metadata.

For a stronger rollback path, make a SQLite backup before machine mapping changes:

```bash
cp codes.db "codes.db.pre-dev-admin-change.$(date +%Y%m%d-%H%M%S).bak"
```

To roll back from a DB backup:

```bash
# 1. Stop the backend (Ctrl-C in its terminal, or stop its supervisor).
# 2. Keep the current file in case the backup turns out to be the wrong one.
mv codes.db "codes.db.rolled-back.$(date +%Y%m%d-%H%M%S)"
# 3. Restore.
cp codes.db.pre-dev-admin-change.<timestamp>.bak codes.db
# 4. Start the backend again.
source .venv/bin/activate && python -m backend.app
```

Restoring an older `codes.db` also rolls back codes, usage sessions, and the audit log — not
just the setting you wanted to undo. Prefer changing the setting back through the panel (the
Change history tab shows the previous value) and keep the DB restore for machine-mapping
mistakes.

There is intentionally **no config import in the panel**. A bad import could corrupt machine
mapping or settings during beta, and the export format has not yet proven itself. Export plus a
SQLite backup is the supported rollback path for now.

## Editable settings

The settings editor is whitelist-based. It does not allow arbitrary database writes. Every key,
its type, range, and risk level is defined in `SETTING_SCHEMA`
(`backend/services/dev_admin_service.py`) and documented in
[`../../reference/settings-catalog.md`](../../reference/settings-catalog.md).

Editable groups:

- **API/Security**: `cors_allowed_origins` only; secrets are rotate-only
- **Scanner**: `serial_port`, `serial_baudrate`, `scan_timeout`
- **Machine Timing**: `button_select_timeout_sec`, `machine_reservation_minutes`
- **Screen Timing**: `selection_notice_seconds`, `started_notice_seconds`, `error_notice_seconds`, `kiosk_poll_interval_ms`
- **Hardware Timing**: `relay_pulse_duration_sec`, `shelly_http_timeout_sec`, `telemetry_http_timeout_sec`
- **Kiosk Input**: `kiosk_input_mode` (read-only; legacy, see the catalog)
- **Runtime Toggles**: `backend_relay_enabled`, `telemetry_enabled`, `button_box_enabled`
- **Codes**: `code_expiration_days`
- **Provider/Mode**: non-secret Reisa/provider fields, including timeouts, action strings, and the retry worker
- **Logging**: `log_level`

`dev_admin_enabled` is **not** in this list — it lives in the Danger Zone (below).

Scanner, CORS, and log-level changes are restart-sensitive; every timing setting above applies
without a restart, which is what makes iterative tuning possible.

### Review before save

Saving does not write immediately. **Review N changes** opens a diff — `old → new` for each
setting, high-risk first. Changes that can take the kiosk offline or move real hardware
(`backend_relay_enabled` → on, `cors_allowed_origins`, provider switches, secret rotation) each
require their own acknowledgement checkbox before the save button unlocks.

Each field also shows **Reset to default**, and the settings list has a filter box and a
**Changed only** toggle.

### Restart-required banner

After saving a restart-sensitive setting, a banner names exactly which ones are pending and
shows the restart command. The values are already in the database; the running process is still
using the old ones. Restart on the kiosk host with:

```bash
source .venv/bin/activate
python -m backend.app
```

There is deliberately **no restart button**. This repository ships no systemd unit, so there is
no specific service the backend could safely be allowed to restart, and a general one would mean
arbitrary process control from a web page.

## Danger Zone

`dev_admin_enabled` is isolated at the bottom of the Settings page because turning it off is a
one-way door from the browser: it locks every admin out of `/dev/admin` immediately.

Disabling it requires typing `DISABLE DEV ADMIN` exactly. The backend enforces this too — a
`PATCH /api/dev_admin/settings` setting `dev_admin_enabled=false` without
`confirmation_phrase` is rejected with `400`, so the guard cannot be bypassed with `curl`.

The recovery command is displayed inline on the page, and is the same snippet as **Enable the
panel** above.

## Diagnostics

The Diagnostics tab is the tuning instrument. Four views:

- **Live readings** — per machine: the current metric value, which band it falls in
  (`high` / `mid` / `low` relative to the configured thresholds), how long it has been above or
  below, run state, and time since the last successful read. A rolling chart plots the last ~120
  samples with the ON and OFF thresholds drawn as reference lines. This is how you pick
  `on_threshold` / `off_threshold`, and how you tell whether `on_confirm_ms` is too short.
- **Scan log** — recent scans and their outcomes.
- **Change history** — the configuration audit trail (below).
- **Metrics** — runtime counters, gauges, and histograms.

If telemetry polling is disabled, the tab says so: readings will not update and every machine
reports as available.

## Change history (configuration audit log)

Every settings and machine change made through this panel is recorded in the
`settings_audit_logs` table (`backend/models/settings_audit_model.py`): timestamp, source,
what changed, the old and new value, and whether it was high risk or restart-sensitive.

The audit row is written in the same transaction as the change, so the two commit or roll back
together — there is no such thing as an applied change with no audit row.

Secrets are recorded by presence only (`<set>` / `<not set>`). Raw secret values never reach
this table.

Use it when kiosk behaviour changes unexpectedly: find the time it started, and look for the
configuration change just before it.

## Machine Card Layout Editor

The Machine Cards section controls what customers see on the kiosk selection screen:

- display name,
- short label,
- washer/dryer type,
- card order,
- description,
- Active in kiosk.

Saving the Machine Cards section is **all-or-nothing**: every changed card and the display order go to the
backend as one transaction, so a rejected card cannot leave the machines before it already written.

Machine cards in this admin page are **preview-only**. Clicking them does not select, reserve, start, or modify any real machine or kiosk state.

## Active in kiosk

The toggle is intentionally named **Active in kiosk**, not “Visible”.

When off, the machine is removed from the kiosk selection/runtime flow and cannot be selected by customers. It maps to `Machine.is_enabled`, not merely a visual hidden state.

A future production admin system may add a separate visual-only hidden flag, but this beta panel does not overbuild that distinction.

## Advanced / Technical Mapping

Technical mapping is high-risk and lives in the Advanced / Technical Mapping drawer.

Fields can include:

- Shelly IP address,
- relay channel,
- I4 button index,
- metric source,
- telemetry thresholds and debounce timings.

These fields never autosave. Saving high-risk technical mapping requires explicit confirmation because incorrect values can start the wrong physical washer/dryer or break availability reporting.

## Later production evolution

A future production admin system should add:

- separate admin credentials,
- users and roles,
- per-user audit attribution (the change audit exists; the *who* does not),
- safer secret rotation,
- migrations,
- config import/restore workflows (export exists today; restore is deliberately manual — see
  **Config export and backup before risky changes**),
- CSRF/rate limiting where applicable,
- a more complete diagnostics and hardware-test design.
