# Hardware Topology and Telemetry

Code source of truth:
- `backend/models/device_model.py`
- `backend/models/machine_model.py`
- `backend/setup/seed_machines.py`
- `backend/controllers/telemetry.py`
- `backend/controllers/machine_control.py`
- `backend/utils/shelly_control.py`

## Topology model

## Device rows (`devices`)
Each physical endpoint is a `devices` row with:
- `role` (functional category)
- `ip`
- `relay_channel` and/or `input_channel`
- `metric_source`

## Machine rows (`machines`)
Each logical machine maps to:
- one UNI device (`uni_device_id`)
- optional i4 button device (`i4_device_id` + `i4_button_index`)
- per-machine telemetry config (`machine_configs`)

## Seeded default example
From `seed_machines.py` defaults:
- one button box device (`role=button_box`)
- one i4 device (`role=i4`)
- multiple UNI devices for washers/dryers
- machines mapped by `uni_device_name` + `i4_button_index`

## Runtime state store
`MachineStateStore` keeps in-memory runtime fields:
- run state (`available`, `in_use`, `offline`)
- pending start marker
- last telemetry value
- transition timing markers (`above_since`, `below_since`)

## Telemetry sources

Telemetry read behavior uses `device.metric_source`.

## `power`
Read order in code:
1. `GET /rpc/Switch.GetStatus?id=<channel>` and `apower`
2. fallback `GET /status` and `meters[channel].power`
3. fallback `GET /status` and `voltmeter:100.voltage`

## `adc`
- `GET /rpc/Adc.GetStatus?id=<channel>`
- reads `voltage` or `adc`

## `digital`
- `GET /rpc/Input.GetStatus?id=<input_channel>`
- maps boolean state to `1`/`0`

## `voltage` or `voltmeter`
- `GET /rpc/Voltmeter.GetStatus?id=100`
- reads `voltage`

## `none` or missing metric source
- telemetry loop skips polling for that machine.

## Threshold and debounce logic
Per machine config:
- `on_threshold`
- `off_threshold`
- `on_confirm_ms`
- `off_confirm_ms`
- `poll_interval_ms` (minimum effective interval enforced as 500ms)

Band classification:
- `high`: value >= `on_threshold`
- `low`: value <= `off_threshold`
- `mid`: between thresholds

Transitions:
- to `in_use` only after value stays `high` for `on_confirm_ms`
- to `available` from `in_use` only after value stays `low` for `off_confirm_ms`
- failed reads mark machine `offline`
- next successful read from `offline` sets `available`

## Start flow linkage
- Start requests mark machine as pending/unavailable immediately.
- Telemetry `runstate_started` callback triggers commit finalization.
- Telemetry `runstate_stopped` callback triggers completion handling.

## Button box and relay behavior
`machine_control.py` handles button-box relay as follows:
- on code arm: `_activate_button_box()` -> `shelly_switch_on(button_box)`
- on disarm/timeout: `_deactivate_button_box()` -> pulse or switch off depending on `metric_source`

Machine relay behavior:
- controlled by setting `backend_relay_enabled`
- if true, backend sends Shelly ON during start request
- if false, backend skips relay command and still waits for telemetry confirmation

## Failure scenarios and operator meaning

## Scenario: machine always offline
Likely causes:
- wrong IP
- unsupported `metric_source`
- network/routing failure

Check:
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
```
Then inspect logs for `TELEMETRY_READ` errors and `DEVICE_OFFLINE`.

## Scenario: starts requested but never committed
Likely causes:
- telemetry thresholds never cross into confirmed `high`
- machine physically starts but sensor metric does not reflect run state

Check:
- machine config thresholds in DB
- telemetry logs and runstate events

## Scenario: false in-use/false available flapping
Likely causes:
- threshold values too tight
- confirm windows too short for noisy metrics

Action:
- tune `on_threshold`, `off_threshold`, `on_confirm_ms`, `off_confirm_ms` per machine.

## High-risk operations
- Enabling `backend_relay_enabled` without validating IP/channel mappings can trigger wrong hardware.
- Bulk editing `devices` and `machines` during runtime can destabilize button mapping and telemetry state.

## Requires restart
- Changes to scanner serial settings require backend restart (scanner module config is import-time).
- Telemetry definitions are reloaded continuously, but restart is still recommended after major topology changes.

## Unknown / requires verification from code
- Whether any production deployment uses additional device roles beyond those currently referenced (`button_box`, `i4`, UNI roles).
