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

Frontend handling in `App.jsx`:
- `waiting_for_code` -> `ScanScreen`
- `choose_machine` -> `MachineSelectScreen`
- `machine_starting`, `machine_in_use`, `error` -> `ResultScreen`
- unknown state -> `ResultScreen` fallback

## Field semantics
- `state`: machine flow stage
- `message`: operator-facing instruction or error
- `uses_left`: numeric remaining uses when known, else `null`
- `current_machine`: selected/running machine slug or `null`
- `machines`: array of `{id,name,available}` from telemetry store

## Transition map

## `waiting_for_code` -> `choose_machine`
Trigger:
- successful scan ingest (`/api/scan_code` or scanner listener)

Effects:
- code armed for button selection
- machine snapshot attached

## `choose_machine` -> `machine_starting`
Trigger:
- start request accepted (`/api/start_machine` or `/api/i4_event`)

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
Frontend polling frequency:
- every 1000ms (`setInterval` in `App.jsx`)

Frontend API function:
- `pollState()` calls `/api/ui_state` with `X-API-KEY`

Failure behavior in frontend:
- request helper returns `null` on non-2xx or fetch error
- UI keeps last known state because `setUiState` is skipped when response is null

## Auth contract
`/api/ui_state` requires valid API key.
Without it, frontend request fails and state stops updating.

## Timing and timeout settings
State timers in backend logic:
- result display hold windows are short (fixed constants)
- button-arm timeout is driven by `button_select_timeout_sec`
- pending start timeout uses `selection_timeout_sec` with fallback default

Important mismatch:
- `button_select_timeout_sec` is seeded in settings defaults.
- `selection_timeout_sec` is read by code but not seeded by default.

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
- wrong button index mapping

Check:
- `button_select_timeout_sec`
- machine/button mapping in DB

## Unknown / requires verification from code
- No frontend-side retry/backoff policy beyond 1-second polling loop is implemented.
