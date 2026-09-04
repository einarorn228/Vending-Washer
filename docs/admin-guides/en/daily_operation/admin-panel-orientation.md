---
id: admin-panel-orientation
locale: en
canonical: true
title: "Admin panel orientation"
summary: "What the /dev/admin panel is for, what each tab does, what is safe to change, and what to record before changing anything."
category: daily_operation
kind: concept
risk: low
status: published
last_reviewed: 2026-09-03
related_guides:
  - using-diagnostics
  - settings-requiring-restart
  - admin-access-recovery
  - machine-technical-mapping
  - reisa-configuration
related_settings:
  - dev_admin_enabled
  - backend_relay_enabled
  - telemetry_enabled
  - button_box_enabled
  - kiosk_input_mode
  - kiosk_poll_interval_ms
  - selection_notice_seconds
  - started_notice_seconds
  - error_notice_seconds
diagnostics:
  - core
  - kiosk.state
search_aliases:
  - what is this panel
  - which tab do i need
  - is it safe to change this
  - back up before changing settings
  - export the configuration
  - where do i start
---

## What this panel is for {#purpose}

The panel at `/dev/admin` is a temporary beta control surface for the kiosk
backend. It exists so that whoever looks after the site can read the system's
state and adjust it without a terminal: settings, machine cards, diagnostics, a
remote control for the kiosk state machine, and the help you are reading now.

It is not a production admin system. There is one shared admin account, no roles
and no per-person audit — the change log records what changed, not who changed
it. Do not expose it beyond the site's own network.

Getting in needs two things: `dev_admin_enabled` must be on in the backend, and
you must sign in with the admin username and password. If the panel says it is
disabled, or the login is refused, that is
[Admin access and dev/admin panel recovery](guide:admin-access-recovery).

## The tabs {#tabs}

| Tab | What it is for |
|---|---|
| **Overview** | The whole system's current state on one screen, plus **Export current config**. The first place to look for almost anything. |
| **Remote Control** | The kiosk state machine: what the kiosk is showing, **Inject Scan**, **Select Machine**, and **Reset Kiosk**. Useful for reproducing a customer's report without standing at the kiosk. |
| **Diagnostics** | **Live readings** per machine, **Scan log**, **Change history** and **Metrics**. The instrument panel for every telemetry question. |
| **Settings** | The whitelisted settings editor, then **Sensitive Settings** for secret rotation, then the Danger zone at the bottom. |
| **Machine Cards** | How machines are named, labelled and ordered on the kiosk, and the way in to each machine's **Advanced / Technical Mapping**. |
| **Hjálp** | This help hub: guides, search, checklists and the support report. |

Overview and Diagnostics are covered field by field in
[Reading Overview and Diagnostics](guide:using-diagnostics).

## What is safe to change {#safe-changes}

Most of what an operator needs day to day is safe, reversible and applies
immediately.

- **Card presentation.** Display names, short labels, machine type and the order
  machines appear in on the kiosk. These change what the customer reads, never
  what the hardware does. Taking a machine out of **Active in kiosk** on the same
  screen is a different matter — that removes it from the kiosk entirely, and it
  is recorded as a high-risk change.
- **Screen timing.** `selection_notice_seconds`, `started_notice_seconds` and
  `error_notice_seconds` decide how long the kiosk holds each notice before
  returning to the ready screen. `kiosk_poll_interval_ms` decides how often the
  kiosk screen asks the backend for the current state — lower feels snappier and
  costs more load, higher is calmer and laggier.
- **Reading anything.** Overview, all four Diagnostics views, the help hub and the
  support report change nothing at all.

Two things make a change safer regardless of what it is: change one setting at a
time, and read the setting's own description in the panel before you change it.
Saving is a two-step action — **Review N changes** shows every change as old →
new with its risk before anything is written.

## What is high risk {#high-risk}

These are not forbidden; they are the ones to stop and think about. Most of them
demand a confirmation of their own before they are applied — a tick box in the
review dialog, the current API key, an acknowledgement in the mapping drawer, or
a typed phrase — but not all of them do, so the judgement is still yours.

- **`backend_relay_enabled`.** Turning it on means a machine selection sends real
  power to real hardware, and the review dialog makes you acknowledge that
  separately. Turning it off is the fastest way to make a mapping
  problem safe. Either way, tell staff, because with it off the kiosk still
  accepts scans and reserves machines while nothing switches on.
- **Advanced / Technical Mapping.** Shelly addresses, relay channels, I4 button
  indexes, metric sources and thresholds. A wrong value here starts the wrong
  physical machine. See
  [Machine technical mapping](guide:machine-technical-mapping).
- **Provider settings.** Which provider validates codes, its address, its token
  and its action identifiers. A wrong value stops every customer from washing.
  See [Reisa connection and configuration](guide:reisa-configuration).
- **Secret rotation.** **Generate New API Key** and **Update Reisa Token** in
  **Sensitive Settings**. Both require the current API key first, and a new API key
  is shown once and never again.
- **Danger zone.** Turning `dev_admin_enabled` off locks every browser out of
  this panel immediately, and it cannot be turned back on from here. It requires
  typing a confirmation phrase exactly, and the way back is on the kiosk host.
- **`telemetry_enabled`.** With it off nothing reads the machines, so every
  machine reports as available and customers are sent to machines that are
  already running.
- **`cors_allowed_origins`** and the scanner settings. These only take effect
  after the backend is restarted, so a mistake in them can surface hours later.
  See [Settings that need a restart](guide:settings-requiring-restart).

Two settings look like controls and are not quite. `kiosk_input_mode` is legacy:
it is read-only and has no runtime effect today, because touch selection on the
kiosk is always allowed. The setting that actually controls the physical button
box is `button_box_enabled`.

## Back up before you change anything risky {#backup}

There is no undo button in this panel, and no configuration import. Before any
high-risk change, spend the minute it takes to record what things look like now.

1. On Overview, press **Export current config**. It downloads a JSON file
   containing the settings, the machines, the devices, the machine configs and
   the kiosk card layout. Raw secrets are not in it — each secret appears only as
   whether it is set. Keep the file somewhere you will find it again, named for
   the day and the change.
2. Write down, or photograph, the specific fields you are about to change and
   what they currently say. That matters most in **Advanced / Technical Mapping**,
   where the values are per machine and easy to mix up once two of them have been
   edited.
3. Note the time. **Change history** in Diagnostics records every change with its
   old and new value, so knowing roughly when you started is usually enough to
   reconstruct a session.

The export is a record to retype from, not a restore button — nothing in the
panel reads it back. A true rollback means restoring the backend's database file
on the kiosk host, which also rolls back codes, usage sessions and the audit
trail, so it is a maintainer step of last resort. In practice the better path is
almost always to put the value back through the panel, reading the previous value
out of **Change history**.

## Where to look next {#next-steps}

Start with Overview whenever you do not yet know which part of the system is
unhappy, and with Diagnostics whenever you already know it is a machine. Use the
help hub's search rather than browsing when you have a symptom in words: the
guides are indexed by the phrases operators actually use.

When a change is needed, do it in this order: record the current state, make one
change, watch its effect, and only then decide whether a second change is needed.
Almost every difficult situation in this system began as two changes made at
once.
