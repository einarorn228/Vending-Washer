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
- anyone with the API key can unlock this panel while `dev_admin_enabled=true`,
- there are no users, roles, OAuth, audit trails, rate limits, or production-grade account controls.

Do not expose `/dev/admin` or `/api/dev_admin/*` to the public internet.

## Secrets policy for first beta

The first beta panel does not edit or reveal raw secrets. These are read-only/masked metadata only:

- `api_key`
- `admin_password_hash`
- `reisa_bearer_token`

Secret editing and rotation belong in a later production admin system.

## Config export and backup before risky changes

Use **Export current config** in the Overview page before changing risky settings or Advanced / Technical Mapping fields. The export excludes raw secrets and includes only secret `is_set` metadata.

For a stronger rollback path, make a SQLite backup before machine mapping changes:

```bash
cp codes.db "codes.db.pre-dev-admin-change.$(date +%Y%m%d-%H%M%S).bak"
```

To roll back from a DB backup, stop the backend, replace `codes.db` with the backup, then restart the backend.

## Editable settings

The settings editor is whitelist-based. It does not allow arbitrary database writes.

Examples of editable groups:

- Dev/Admin Access: `dev_admin_enabled`
- API/Security: `cors_allowed_origins` only; secrets remain read-only
- Scanner: `serial_port`, `serial_baudrate`, `scan_timeout`
- Machine Timing: `button_select_timeout_sec`, `selection_timeout_sec`
- Runtime Toggles: `backend_relay_enabled`, `telemetry_enabled`, `button_box_enabled`
- Provider/Mode: non-secret Reisa/provider fields
- Logging: `log_level`

Scanner, CORS, and log-level changes should be treated as restart-sensitive.

## Machine Card Layout Editor

The Machine Cards section controls what customers see on the kiosk selection screen:

- display name,
- short label,
- washer/dryer type,
- card order,
- description,
- Active in kiosk.

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
- audit logs,
- safer secret rotation,
- migrations,
- import/restore workflows,
- CSRF/rate limiting where applicable,
- a more complete diagnostics and hardware-test design.
