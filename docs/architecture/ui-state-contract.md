# UI State Contract

Source of truth:
- backend state owner: `backend/controllers/machine_control.py`
- API exposure: `backend/controllers/ui_api.py`
- frontend consumption: `frontend/src/App.jsx`, `frontend/src/api/backend.js`

## Contract ownership
Backend owns state machine and messages.
Frontend is a polling renderer and does not compute machine state.

## `UI_STATE` shape
Defined in backend:

```json
{
  "state": "waiting_for_code",
  "message": "Scan your code to start",
  "uses_left": null,
  "current_machine": null,
  "machines": []
}
```

`GET /api/ui_state` returns a copy with `machines` refreshed from telemetry snapshot.

## Valid `state` values observed in code
- `waiting_for_code`
- `choose_machine`
- `machine_starting`
- `machine_in_use`
- `error`

Frontend handling in `frontend/src/kiosk/KioskRouter.jsx` (`App.jsx` only picks the
route: kiosk, `/dev/admin`, `/dev/kiosk-preview`, or `/help`):
- `waiting_for_code` -> `HomeScreen`
- `choose_machine` -> `SelectMachineScreen`
- `machine_starting` -> `StartingScreen`
- `machine_in_use` -> `InUseScreen`
- `error` -> `ErrorScreen`
- unknown state -> `ErrorScreen` fallback

All five components live in `frontend/src/kiosk/screens/`, and every one of them is
wrapped by `KioskAppShell`.

## Field semantics
- `state`: machine flow stage
- `message`: operator-facing instruction or error
- `uses_left`: numeric remaining uses when known, else `null`
- `current_machine`: selected/running machine slug or `null`
- `machines`: array of `{id,name,available}` from telemetry store
- `input_mode`: legacy compatibility metadata; may still appear in `/api/ui_state`
- `button_box_enabled`: backend boolean flag for button-box input enablement

Interaction rules:
- `choose_machine` means touchscreen machine cards are interactive.
- `input_mode` must not be treated as source-of-truth for touch interactivity.
- `button_box_enabled` is useful for diagnostics/display but is not required for touch selection.

## Transition map

## `waiting_for_code` -> `choose_machine`
Trigger:
- successful scan ingest (`/api/scan_code` or scanner listener)

Effects:
- code/session armed for machine selection
- machine snapshot attached

## `choose_machine` -> `machine_starting`
Trigger:
- start request accepted (`/api/start_machine`, `/api/touch_select_machine`, or `/api/i4_event`)

Effects:
- pending start set
- optional relay command if enabled
- selection timeout timer starts

## `machine_starting` -> `machine_in_use`
Trigger:
- telemetry callback `runstate_started` confirming actual run

Effects:
- provider commit runs
- usage lifecycle updates
- short UI timer then reset

## any -> `error`
Trigger examples:
- invalid/missing scan
- start rejection
- operation failures

Effects:
- error message shown briefly
- timer resets to `waiting_for_code`

## `machine_starting` -> `waiting_for_code` (timeout path)
Trigger:
- selection timeout callback

Effects:
- pending start cleared
- optional usage session marked timed out

## Polling behavior
Frontend polling lives in `frontend/src/kiosk/hooks/useUiStatePolling.js`, not in
`App.jsx`.

Frontend polling frequency:
- default 1000 ms (`DEFAULT_POLL_INTERVAL_MS`)
- the backend owns the cadence: each `/api/ui_state` response may carry
  `poll_interval_ms` (from the `kiosk_poll_interval_ms` setting), and the hook
  re-arms its `setInterval` whenever that value changes
- values outside 250–10000 ms are rejected and the default is used instead

Frontend API function:
- `pollState()` calls `/api/ui_state` with `X-API-KEY`

Failure behavior in frontend:
- request helper returns `null` on non-2xx or fetch error
- UI keeps last known state because `setUiState` is skipped when response is null

## Auth contract
`/api/ui_state` requires valid API key.
Without it, frontend request fails and state stops updating.

## Timing and timeout settings
State timers in backend logic (all in `backend/controllers/machine_control.py`):
- result display hold windows are settings, not fixed constants:
  `selection_notice_seconds`, `started_notice_seconds`, `error_notice_seconds`
  (`machine_control.py:625-634`). The module constants next to them
  (`SELECTION_NOTICE_SECONDS` and friends, `:47-49`) are only fallbacks for a
  missing or unparseable value, and each reader clamps to a sane range.
- button-arm timeout is driven by `button_select_timeout_sec`
- the machine-selection/pending-start timeout is derived from
  `machine_reservation_minutes` — `_selection_timeout_seconds()`
  (`machine_control.py:589-600`) reads that setting and multiplies by 60,
  falling back to `SELECTION_TIMEOUT_SECONDS` if it is missing or non-positive.

Note:
- `button_select_timeout_sec` and `machine_reservation_minutes` are both seeded
  in settings defaults.
- There has never been a `selection_timeout_sec` setting. Earlier revisions of
  this document named one; no code has ever read it. See
  `docs/reference/settings-catalog.md`.

## Failure modes and symptoms

## Symptom: UI stuck on old message
Likely cause:
- polling failures returning null

Check:
- browser console for request errors
- backend `/api/ui_state` with curl and API key

## Symptom: “System busy. Please wait.” on valid scan
Likely cause:
- state not in `waiting_for_code`

Check:
- current `state` from `/api/ui_state`
- pending timers or ongoing machine start flow

## Symptom: choose screen shown but button press rejected
Likely cause:
- armed code timed out
- `button_box_enabled` is false
- wrong button index mapping

Check:
- `button_select_timeout_sec`
- machine/button mapping in DB

## Unknown / requires verification from code
- No frontend-side retry/backoff policy beyond 1-second polling loop is implemented.
