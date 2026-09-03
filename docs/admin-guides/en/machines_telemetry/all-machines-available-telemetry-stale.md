---
id: all-machines-available-telemetry-stale
locale: en
canonical: true
title: "All machines show available while telemetry is stale"
summary: "Every machine looks free on the kiosk, so customers are sent to machines that are already running."
category: machines_telemetry
kind: troubleshooting
risk: medium
status: published
last_reviewed: 2026-09-03
common_problem_rank: 3
related_guides:
  - machine-unavailable
  - machine-does-not-start
  - no-telemetry-reading
related_settings:
  - telemetry_enabled
diagnostics:
  - machine.identity
  - machine.telemetry
  - settings.telemetry
search_aliases:
  - everything shows free
  - readings do not update
  - customer sent to a running machine
  - availability is wrong for every machine
checks:
  - id: telemetry-setting-on
    question: "Is telemetry polling enabled in Settings?"
    look_for: "Settings, the Shelly / Runtime Toggles group, Telemetry polling enabled."
    expected: "On. Off explains every machine reporting available."
    route: settings
    diagnostics: settings.telemetry
  - id: telemetry-off-banner
    question: "Does Diagnostics show the telemetry-off warning banner?"
    look_for: "The red banner at the top of the Diagnostics tab."
    expected: "No banner when polling is running."
    route: diagnostics
    diagnostics: settings.telemetry
  - id: last-read-age
    question: "Is Last read climbing on every machine?"
    look_for: "Diagnostics, Live readings, Last read on each card."
    expected: "A small number that resets, roughly the machine's poll interval."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: values-frozen
    question: "Do the values change at all while a machine is definitely running?"
    look_for: "Diagnostics, Live readings, the value and the chart for a running machine."
    expected: "The value moves. A value frozen to the same number is the symptom."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: run-state-all-available
    question: "Does every machine report run state available, including one you can hear running?"
    look_for: "Diagnostics, Live readings, Run state on every card."
    expected: "A running machine should read in_use."
    route: diagnostics
    diagnostics: machine.identity
---

## When to use this {#when-to-use}

Use this guide when the kiosk shows **every** machine as available, including
machines that are visibly or audibly running, and customers end up paying for a
machine that is already in use.

This is the more expensive failure of the two availability problems, because the
customer's use is spent before anyone notices. If only **one** machine is wrong,
and it is stuck the other way — showing as busy while it is idle — read
[Machine shows unavailable while it is idle](guide:machine-unavailable).

## Possible causes {#causes}

Machines only ever change state because telemetry reads them. When the readings
stop, every machine keeps the state it had at that moment, and a backend that
has just been started holds every machine as available. So "everything is free"
is almost always the shape of *nothing is being read*, not of a device fault:
devices that stop answering individually are marked offline and disappear from
selection instead.

**Telemetry polling is switched off.** With `telemetry_enabled` off, the polling
loop keeps running but reads nothing at all. Diagnostics says so directly with a
red banner, and the live values stand still.

**The running backend is not the one you configured.** This is the recorded
field incident: polling had been turned off, and the process that was running
was not picking up the change either, so every machine reported available for a
whole afternoon. The operator-visible signal is the same in both halves —
**Last read** climbing on every card while the values stay frozen.

**Nothing at all was ever read.** On a backend where polling has never run,
values show as dashes rather than as frozen numbers, and Last read shows a dash
too.

## Steps {#steps}

1. Open `/dev/admin`, go to Diagnostics and stay on **Live readings**. Look at
   the top of the tab first: a red telemetry-off banner answers the question on
   its own.
2. Watch the cards for about ten seconds. Note whether **Last read** resets to a
   small number, or keeps counting up on every machine at once.
3. Start or find a machine you know is running and compare its value and band
   text against what you can hear. A running machine that reads the same number
   as an idle one is not being read.
4. Go to Settings, open the **Shelly / Runtime Toggles** group, and check
   **Telemetry polling enabled** (`telemetry_enabled`). If it is off, turning it on is the fix; it takes effect
   without a restart. Change only this one setting.
5. Go back to Diagnostics and confirm recovery: **Last read** should drop back to
   a small number, values should start moving, and a running machine should
   switch to `in_use` after its ON confirm time.
6. If the setting was already on and the readings are still frozen, the running
   backend is not applying the configuration. Note that, and stop — restarting
   the backend on the kiosk host is a maintainer step, and the panel shows the
   exact command in its restart banner when one is needed.
7. Until availability is trustworthy again, tell staff not to rely on the kiosk
   screen for which machines are free.

> [!WARNING]
> While telemetry is stale the kiosk cannot tell a busy machine from a free one.
> Treat every machine as unknown until Last read is small again on every card.

## If this did not fix it {#escalate}

Escalate immediately if customers are still being sent to running machines
after telemetry polling is confirmed on, or if the values stay frozen.

Use **Copy support report** at the bottom of this guide and send it with: how
many machines are affected, the Last read values you saw, whether the telemetry
banner was showing, and roughly when the first customer complained.
