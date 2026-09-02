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

## `dev_admin_enabled`
- Default/seed: `false`
- Consumed by: `/api/dev_admin/*` kill-switch checks in `backend/controllers/dev_admin_api.py`
- Risk: **High** (enables temporary beta admin surface)
- Restart needed: No
- Operator notes: keep disabled unless actively using the trusted-local beta panel.

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
  - For kiosk / E2E testing, use `python -m backend.setup.enable_hardware_e2e` then restart backend; see [`../operations/runbooks/kiosk-and-e2e-testing.md`](../operations/runbooks/kiosk-and-e2e-testing.md).

## `button_box_enabled`
- Default/seed: `false`
- Type: bool-like string setting
- Accepted true values: `"true"`, `"1"`, `"yes"`, `"on"` (case-insensitive)
- False examples: `"false"`, `"0"`, `"no"`, `"off"`, empty string, or missing key
- Consumed by:
  - button-box input acceptance in `backend/controllers/ui_api.py` (`/api/i4_event`)
  - button-box arming/activation in `backend/controllers/machine_control.py` (`arm_code`)
- Risk: **High** (changes accepted kiosk input paths)
- Restart needed: No
- Operator notes:
  - Controls whether the physical button box is accepted/activated as a **secondary** machine-selection source.
  - Touchscreen machine selection is still available during `choose_machine` regardless of this setting.
  - Separate from `backend_relay_enabled`: this setting gates button-box input behavior, while `backend_relay_enabled` gates real relay/Shelly actuation.

## `kiosk_input_mode` (legacy; no runtime effect)
- Default/seed: `hardware_buttons`
- Consumed by: echoed on `/api/ui_state` as `input_mode`, then read by `frontend/src/kiosk/adapters/inputModeAdapter.js`
- Risk: **Low**
- Restart needed: No
- Operator notes:
  - **This setting currently changes nothing.** `createInteractionPolicy` hardcodes `allowTouchMachineSelect: true`, and the one value it does derive (`allowTouchPrimaryActions`) is not consumed by any component.
  - Exposed **read-only** in the dev/admin panel so operators can see it without being misled into tuning it.
  - Use `button_box_enabled` to control the physical button box.
  - Either wire this up or delete it before the production admin system; leaving dead configuration in place invites wasted debugging.

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
- Default/seed: `/dev/ttyACM0`
- Consumed by: `backend/controllers/qr_scanner.py`, `tools/test_scanner.py`
- Risk: **Medium**
- Restart needed: **Yes** for scanner module import-time initialization
- Operator notes: set explicitly per host OS/device. Newland FM3080 USB CDC on Pi: [`../operations/runbooks/scanner-newland-fm3080-cdc.md`](../operations/runbooks/scanner-newland-fm3080-cdc.md).

## `serial_baudrate`
- Default/seed: `9600`
- Consumed by: scanner serial init
- Risk: **Medium**
- Restart needed: **Yes**
- Operator notes: must match scanner hardware settings.

## `scan_timeout`
- Default/seed: `3`
- Consumed by: scanner serial init/read timeout
- Risk: **Low/Medium**
- Restart needed: **Yes**
- Operator notes: affects scanner responsiveness and CPU wake profile.

## `code_expiration_days`
- Default/seed: `0` (seeded; `0` means codes never expire)
- Consumed by: code generation (`backend/controllers/code_generator.py`)
- Risk: **Medium**
- Restart needed: No
- Operator notes: only affects codes created after the change; existing codes keep their original expiry.

---

## Screen timing (beta tuning)

All of these are read on demand, so a change from the dev/admin panel applies to the
next kiosk interaction with no restart. Each falls back to the constant in
`backend/controllers/machine_control.py` if the row is missing or unparseable.

## `selection_notice_seconds`
- Default/seed: `3.0` — Range: `0.5`–`30`
- Consumed by: `machine_control.selection_notice_seconds()` → reset timer after entering `machine_starting`
- Risk: **Low** — Restart needed: No
- Operator notes: how long the kiosk waits on the starting screen before falling back to ready when telemetry never confirms.

## `started_notice_seconds`
- Default/seed: `3.0` — Range: `0.5`–`30`
- Consumed by: `machine_control.started_notice_seconds()` → reset timer after a confirmed start
- Risk: **Low** — Restart needed: No
- Operator notes: raise if customers walk away before reading the confirmation.

## `error_notice_seconds`
- Default/seed: `3.0` — Range: `1`–`30`
- Consumed by: `machine_control.show_error_state()` when no explicit hold is passed
- Risk: **Low** — Restart needed: No

## `kiosk_poll_interval_ms`
- Default/seed: `1000` — Range: `250`–`10000`
- Consumed by: served on `/api/ui_state` as `poll_interval_ms`; honoured by `frontend/src/kiosk/hooks/useUiStatePolling.js`
- Risk: **Medium** — Restart needed: No (the kiosk re-arms its timer on the next poll)
- Operator notes: lower feels snappier but increases Pi load; higher is calmer but laggier.

---

## Hardware timing (beta tuning)

## `relay_pulse_duration_sec`
- Default/seed: `1.0` — Range: `0.1`–`10`
- Consumed by: `machine_control.relay_pulse_duration_sec()` → `send_shelly_pulse(duration=...)`
- Risk: **High** (real relay actuation) — Restart needed: No
- Operator notes: machines that ignore a short pulse may need a longer one. Verify wiring before experimenting with `backend_relay_enabled=true`.

## `shelly_http_timeout_sec`
- Default/seed: `3.0` — Range: `1`–`15`
- Consumed by: pushed into `backend/utils/shelly_control.py` via `set_http_timeout()` from `machine_control._refresh_shelly_timeout()` on every actuation
- Risk: **Medium** — Restart needed: No
- Operator notes: raise on slow or unreliable Wi-Fi to the machines. The Gen1/Gen2 probe uses `min(2.0, this)`.

## `telemetry_http_timeout_sec`
- Default/seed: `5.0` — Range: `1`–`30`
- Consumed by: `backend/controllers/telemetry.py` (`_refresh_http_timeout`, refreshed once per poll-loop pass)
- Risk: **Medium** — Restart needed: No
- Operator notes: raise on a busy network; too low shows as repeated failed telemetry reads.

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
- `button_select_timeout_sec` and `machine_reservation_minutes` are different settings with different code paths.
- `button_select_timeout_sec` bounds the armed window for physical button-box selection (`_button_timeout_seconds`).
- `machine_reservation_minutes` bounds how long a selected machine stays reserved (`_selection_timeout_seconds`), and it is the value the kiosk shows the customer on the starting screen.
- There is no `selection_timeout_sec` setting. It was documented previously but no code has ever read it; use `machine_reservation_minutes`.

## `machine_card_layout`
- Default/seed: optional/missing; runtime creates safe defaults when absent
- Consumed by: machine-card decoration for kiosk snapshots and beta dev/admin machine layout editor
- Risk: **Medium/High** (affects kiosk machine card order/type/labels)
- Restart needed: No
- Operator notes: stored as JSON string. Internal machine keys remain in `machines.name`; this layout should not be used to rename internal IDs.
