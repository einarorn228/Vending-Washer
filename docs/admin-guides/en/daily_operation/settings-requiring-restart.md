---
id: settings-requiring-restart
locale: en
canonical: true
title: "Settings that need a restart"
summary: "Which saved settings the running backend keeps ignoring until it is restarted, how to restart it, and how to tell that it worked."
category: daily_operation
kind: concept
risk: medium
status: published
last_reviewed: 2026-09-03
related_guides:
  - admin-panel-orientation
  - scanner-not-scanning
related_settings:
  - cors_allowed_origins
  - serial_port
  - serial_baudrate
  - scan_timeout
  - log_level
diagnostics:
  - core
  - scanner.status
  - settings.scanner
actions:
  - restart_backend
search_aliases:
  - setting saved but nothing changed
  - restart required banner
  - how to restart the backend
  - scanner setting not applied
  - restart the kiosk backend
---

## Which settings need a restart {#restart-list}

Five settings are read once while the backend starts and are not looked at again
while it runs. Saving one of them writes the new value to the database, but the
running process keeps using the old one until it is restarted.

| Setting | Settings group | Label in the panel | What it controls |
|---|---|---|---|
| `cors_allowed_origins` | **API / Security** | CORS allowed origins | Which browser origins the backend will answer at all. |
| `serial_port` | **Scanner** | Serial port | The device path the QR scanner is opened on. |
| `serial_baudrate` | **Scanner** | Serial baud rate | The speed the scanner's serial connection is opened at. |
| `scan_timeout` | **Scanner** | Scan timeout | The read timeout used when the scanner connection is opened. |
| `log_level` | **Logging / Diagnostics** | Log level | How much detail the backend writes to its logs. |

The panel tells you this in three places, and none of them is a status check:

- In the review dialog, before you save, each affected change carries a **restart
  required** badge and a line saying how many of the changes only take effect
  after a restart.
- After saving, a banner appears at the top of the panel naming the settings by
  their labels and showing the command to run.
- In Diagnostics, **Change history**, each of those rows carries a **restart**
  badge, so a change made days ago and never followed by a restart is still
  visible.

The banner is a reminder held in your browser session. It does not ask the
backend whether a restart has happened, and it stays until **Dismiss** is
pressed. A dismissed banner is not evidence that anything was restarted.

## Why these and not the others {#why}

The three scanner settings are used at the moment the serial connection to the
scanner is opened, which happens once during startup. Nothing re-opens that
connection while the backend runs, so a new port or baud rate simply never
reaches the hardware until the next start. `cors_allowed_origins` is applied when
the web layer is configured at startup, and `log_level` when the logger is set
up, both for the same reason.

Everything else in the panel is read at the moment it is needed. Screen dwell
times, poll intervals, the relay and telemetry toggles, the reservation window,
the provider settings and every per-machine threshold are looked up on each use,
so a saved change is visible on the very next scan, start or poll. That is what
makes iterative tuning possible, and it is why a setting that seems to do nothing
is worth checking against the list above before anything else is suspected.

## How to restart {#restart}

There is no restart button in the panel, deliberately: the repository ships no
service definition, so there is no specific process the panel could safely be
allowed to restart, and a general one would mean arbitrary process control from a
web page.

The restart is done on the kiosk host, from the repository root: stop the running
backend, then start it again with the command the banner shows.

```bash
source .venv/bin/activate && python -m backend.app
```

Restarting takes the kiosk out of service for as long as it takes to come back
up. Do it when nobody is mid-wash if you can, and tell staff before you do it —
a scan during the restart is simply not answered.

## How to tell the restart took effect {#verify}

Do not use the banner, and do not use **Status read at** on Overview: that
timestamp is generated fresh on every status request and says nothing about when
the process started.

The reliable check is in Diagnostics, **Metrics**. Look for
`uptime_seconds_total`. After a real restart it is a small number counting up
from zero again; if it is still large, the process you are looking at is the old
one.

For the scanner settings there is a second, more meaningful check. On Overview,
**Scanner port** shows the configured value — that is the saved setting, not proof
of anything — but **Scanner available** reflects the running process: `yes` means
the backend actually managed to open the port it is now configured with. Then
scan one code and confirm a new row appears in Diagnostics, **Scan log**. If
**Scanner available** reads `no` after the restart, the new port or baud rate is
wrong for this hardware, and
[Scanner is not scanning](guide:scanner-not-scanning) picks up from there.

For `log_level`, the evidence is in the backend's own log output on the host: a
lower level starts producing more lines immediately after the restart.

For `cors_allowed_origins`, the evidence is that the panel and the kiosk screen
still load and still reach the backend from the browsers that need them. Check
that from each device that matters straight after the restart, not later — a
wrong value here is much easier to repair while you still know what changed.
