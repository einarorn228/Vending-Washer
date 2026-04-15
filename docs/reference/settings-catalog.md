# Settings Catalog

## Purpose
Canonical reference for settings stored in the `settings` table.

Use this file before changing settings via:
- bootstrap scripts,
- admin settings endpoints,
- direct DB updates.

---

## Settings table overview
- Model: `backend/models/setting_model.py` (`Settings` with `key`, `value`).
- Primary defaults source: `backend/setup/seed_settings.py` (`DEFAULT_SETTINGS`).
- Dynamic reads are spread across backend modules.

General cautions:
- values are stored as strings,
- type coercion happens at read sites,
- bad values may silently fall back to code defaults.

---

## Risk levels used in this catalog
- **Low**: mostly cosmetic/observability; easy recovery.
- **Medium**: affects runtime behavior but usually reversible quickly.
- **High**: can block auth/access, provider commits, or machine control safety.

---

## Catalog (AI-parseable)

## `admin_username`
- Default/seed: `admin`
- Consumed by: admin auth check in `backend/flask_server.py`
- Risk: **High** (admin access)
- Restart needed: No (read at request time)
- Operator notes: keep synced with credential distribution process.

## `admin_password_hash`
- Default/seed: SHA-256 of `admin`
- Consumed by: admin auth check in `backend/flask_server.py`
- Risk: **High** (admin access)
- Restart needed: No
- Operator notes: rotate immediately after first install.

## `api_key`
- Default/seed: generated on first run if missing
- Consumed by:
  - UI API auth (`backend/controllers/ui_api.py`)
  - admin auth wrapper (`backend/flask_server.py`)
  - scripts/readers (`backend/scripts/get_api_key.py`)
- Risk: **High** (all API access control)
- Restart needed: No (value read per request)
- Operator notes: update kiosk localStorage / `VITE_API_KEY` after rotation.

## `cors_allowed_origins`
- Default/seed: `http://localhost`
- Consumed by: Flask CORS init in `backend/flask_server.py`
- Risk: **Medium** (browser/API connectivity + exposure)
- Restart needed: **Yes likely** (loaded at app init)
- Operator notes: admin endpoint can update setting, but app restart is safest to apply runtime CORS policy.

## `log_level`
- Default/seed: `INFO`
- Consumed by: logger configuration (`backend/utils/logger.py`), unless env `LOG_LEVEL` overrides
- Risk: **Low/Medium**
- Restart needed: **Yes** for predictable effect
- Operator notes: use `LOG_LEVEL` env for temporary override.

## `button_select_timeout_sec`
- Default/seed: `45`
- Consumed by: armed-code timeout logic in `backend/controllers/machine_control.py`
- Risk: **Medium**
- Restart needed: No (read on demand)
- Operator notes: too low => user timeouts; too high => stale armed windows.

## `selection_timeout_sec`
- Default/seed: not in `DEFAULT_SETTINGS`; runtime reads key with fallback from `backend/controllers/machine_control.py`
- Consumed by: pending start timeout in `backend/controllers/machine_control.py`
- Risk: **Medium**
- Restart needed: No
- Operator notes: if absent/invalid, code falls back to hardcoded default.

## `backend_relay_enabled`
- Default/seed:
  - missing key is ensured as `false` by `ensure_backend_relay_setting_exists` in `backend.app` startup path
  - `is_backend_relay_enabled` falls back to `"false"` when the key is missing (`backend/models/setting_model.py`)
- Consumed by: Shelly actuation in `backend/controllers/machine_control.py` — washer/dryer start relay **and** button-box ON/OFF/pulse during armed scan window
- Risk: **High** (real relay actuation behavior)
- Restart needed: No
- Operator notes:
  - When `false`, backend skips Shelly ON for machine start and skips button-box relay commands (UI/API simulation without firing hardware).
  - When `true`, backend issues Shelly commands during start and while a code is armed for i4 selection.
  - Startup path matters: `python -m backend.flask_server` does not call `ensure_backend_relay_setting_exists`, so ensure the key exists before relying on defaults.

## `provider_default`
- Default/seed: `local`
- Consumed by: provider selection (`backend/providers/provider_selector.py`)
- Risk: **High** (entitlement/commit path)
- Restart needed: No (resolved during flow)
- Operator notes: switching provider mode changes scan/start semantics.

## `provider_reisa_enabled`
- Default/seed: `false`
- Consumed by: provider selection gate (`backend/providers/provider_selector.py`)
- Risk: **High**
- Restart needed: No
- Operator notes: `provider_default=reisa` is ignored unless this is truthy.

## `reisa_base_url`
- Default/seed: empty
- Consumed by: Reisa client construction (`backend/providers/provider_selector.py` -> `ReisaProvider`)
- Risk: **High** (integration availability)
- Restart needed: No (new provider instances read current settings)
- Operator notes: must be valid when Reisa mode enabled.

## `reisa_bearer_token`
- Default/seed: empty
- Consumed by: Reisa client auth header
- Risk: **High**
- Restart needed: No
- Operator notes: missing/invalid token causes auth failures (401/403 categories).

## `reisa_connect_timeout_ms`
- Default/seed: `1500`
- Consumed by: Reisa client timeout tuple
- Risk: **Medium**
- Restart needed: No
- Operator notes: too low can create false network timeouts.

## `reisa_read_timeout_ms`
- Default/seed: `2500`
- Consumed by: Reisa client timeout tuple
- Risk: **Medium**
- Restart needed: No
- Operator notes: tune with real network latency and provider response profile.

## `reisa_action_start`
- Default/seed: `WASHING_MACHINE_START`
- Consumed by: Reisa provider commit start status action
- Risk: **High** (contract correctness)
- Restart needed: No
- Operator notes: incorrect action strings can cause request rejection.

## `reisa_action_completion`
- Default/seed: `WASHING_MACHINE_COMPLETE`
- Consumed by: Reisa provider completion status action
- Risk: **High**
- Restart needed: No
- Operator notes: validated by hardening tests; avoid arbitrary edits.

## `reisa_retry_worker_enabled`
- Default/seed: `false`
- Consumed by: retry worker loop settings gate (`backend/services/reisa_retry_service.py`)
- Risk: **High** (automated external replay behavior)
- Restart needed: No (worker loop checks setting periodically)
- Operator notes: enable only with clear operational ownership.

## `reisa_retry_worker_interval_sec`
- Default/seed: `30`
- Consumed by: retry worker poll interval
- Risk: **Medium**
- Restart needed: No
- Operator notes: low values increase retry traffic/log volume.

## `reisa_retry_worker_batch_size`
- Default/seed: `20`
- Consumed by: retry worker due-job batch limit
- Risk: **Medium**
- Restart needed: No
- Operator notes: oversizing can create burst load.

## `serial_port`
- Default/seed: not seeded; default fallback used in scanner code (`/dev/ttyACM0`)
- Consumed by: `backend/controllers/qr_scanner.py`, `tools/test_scanner.py`
- Risk: **Medium**
- Restart needed: **Yes** for scanner module import-time initialization
- Operator notes: set explicitly per host OS/device. Newland FM3080 USB CDC on Pi: [`../operations/runbooks/scanner-newland-fm3080-cdc.md`](../operations/runbooks/scanner-newland-fm3080-cdc.md).

## `serial_baudrate`
- Default/seed: not seeded; fallback `9600`
- Consumed by: scanner serial init
- Risk: **Medium**
- Restart needed: **Yes**
- Operator notes: must match scanner hardware settings.

## `scan_timeout`
- Default/seed: not seeded; fallback `1`
- Consumed by: scanner serial init/read timeout
- Risk: **Low/Medium**
- Restart needed: **Yes**
- Operator notes: affects scanner responsiveness and CPU wake profile.

## `code_expiration_days`
- Default/seed: not seeded; code fallback `0`
- Consumed by: code generation (`backend/controllers/code_generator.py`)
- Risk: **Medium**
- Restart needed: No
- Operator notes: controls when codes get expiration timestamps.

---

## Settings update methods

### Admin API (authenticated)
```bash
curl -X PUT -u admin:<password> -H "X-API-KEY: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"value":"60"}' \
  http://127.0.0.1:5000/admin/settings/button_select_timeout_sec
```

### CORS helper endpoint
```bash
curl -X PUT -u admin:<password> -H "X-API-KEY: <API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"origins":["http://localhost:3000"]}' \
  http://127.0.0.1:5000/admin/settings/cors
```

### Scripted/DB direct updates
Prefer API unless recovery constraints require direct DB intervention.

---

## Operator safety rules
1. Change one high-risk setting at a time.
2. Capture old/new values before edit.
3. Verify with targeted endpoint/flow after each change.
4. Restart backend when changing startup-sensitive behavior (especially CORS/logging/scanner port assumptions).

---

## Related docs
- Runtime lifecycle: [`../architecture/runtime-lifecycle.md`](../architecture/runtime-lifecycle.md)
- Install/bootstrap: [`../operations/runbooks/install-and-bootstrap.md`](../operations/runbooks/install-and-bootstrap.md)
- Reisa operator playbook: [`../integrations/reisa/runbooks/reisa-operator-playbook.md`](../integrations/reisa/runbooks/reisa-operator-playbook.md)


## Timeout key gotcha
- `button_select_timeout_sec` and `selection_timeout_sec` are different settings with different code paths.
- Only `button_select_timeout_sec` is seeded by default.
- If you need non-default selection pending timeout, add/update `selection_timeout_sec` explicitly.
