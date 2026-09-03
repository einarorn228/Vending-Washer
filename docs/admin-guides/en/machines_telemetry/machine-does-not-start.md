---
id: machine-does-not-start
locale: en
canonical: true
title: "Machine does not start after selection"
summary: "The code was accepted and a machine was chosen, but the machine never runs."
category: machines_telemetry
kind: troubleshooting
risk: medium
status: published
last_reviewed: 2026-09-03
common_problem_rank: 2
related_guides:
  - machine-unavailable
  - admin-panel-orientation
related_settings:
  - backend_relay_enabled
  - telemetry_enabled
  - machine_reservation_minutes
  - selection_notice_seconds
  - shelly_http_timeout_sec
diagnostics:
  - kiosk.state
  - machine.identity
  - machine.telemetry
  - machine.thresholds
  - settings.relay
search_aliases:
  - washer will not start
  - nothing happens after choosing a machine
  - machine gets no power
  - start does not work
checks:
  - id: program-selected
    question: "Was a program selected on the machine itself after it was chosen on the screen?"
    look_for: "The machine's own dial or buttons, not the kiosk screen."
    expected: "The machine only runs once its own program is started."
  - id: kiosk-message
    question: "What did the kiosk show right after the machine was chosen?"
    look_for: "Overview, Current UI state, while you repeat the attempt."
    expected: "A start message naming the machine. Machine start failed means the relay command did not get through."
    route: overview
    diagnostics: kiosk.state
  - id: relay-control-enabled
    question: "Is backend relay control enabled?"
    look_for: "Overview, Backend relay."
    expected: "Enabled. When it is disabled the backend never sends a power command to any machine."
    route: overview
    diagnostics: settings.relay
  - id: pending-start-held
    question: "Is the machine still holding a pending start?"
    look_for: "Diagnostics, Live readings, Pending start for that machine."
    expected: "Yes right after an attempt, then no once the reservation ends."
    route: diagnostics
    diagnostics: machine.identity
  - id: reading-responds
    question: "Does the live reading move when the machine is started?"
    look_for: "Diagnostics, Live readings, the value and Last read for that machine."
    expected: "The value rises within a few seconds of the machine actually running."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: reading-reaches-on-threshold
    question: "Does the reading reach the ON threshold and stay there?"
    look_for: "Diagnostics, Live readings, the band text and Above for against ON confirm."
    expected: "At or above ON threshold, held for at least the ON confirm time."
    route: diagnostics
    diagnostics: machine.thresholds
---

## When to use this {#when-to-use}

Use this guide when a scan was accepted, the customer chose a machine on the
kiosk, the kiosk answered with a start message naming that machine, and the
machine still never runs. A few seconds later the kiosk returns to the ready
screen on its own.

If the customer could not choose the machine at all because the card said
*In use*, you are in a different situation: read
[Machine shows unavailable while it is idle](guide:machine-unavailable) instead.

One thing you can tell the customer straight away: a use is only counted when
the backend sees the machine actually running. A selection that never turned
into a run does not consume a use, so the same code can be scanned again.

## Possible causes {#causes}

**Relay control is switched off.** The backend only sends a power command when
`backend_relay_enabled` is on. When it is off, the kiosk still shows the normal
start message and reserves the machine, but nothing is sent to the hardware.
This is the dry-run mode used on the bench, and it is the most common reason a
selection looks accepted and nothing happens.

**The power command did not get through.** With relay control on, the backend
asks the machine's Shelly device to switch its relay on, and retries once. If
the device does not answer inside `shelly_http_timeout_sec`, the reservation is
released immediately and the kiosk shows *Machine start failed*. That points at
the device or the network, not at the kiosk.

**The machine has power but no program was started on it.** The kiosk message
asks the customer to select a program on the machine. Until they do, the machine
draws almost nothing and looks idle to the backend.

**The run was never confirmed.** The kiosk only reaches the *started* screen
when telemetry sees the machine's reading at or above its ON threshold and
holds it there for the ON confirm time. If the reading never gets that high, or
drops back too soon, no confirmation arrives. The kiosk screen resets after
`selection_notice_seconds`, and the machine stays reserved until
`machine_reservation_minutes` runs out.

**Telemetry polling is off.** With `telemetry_enabled` off nothing reads the
machines at all, so a real run can never be confirmed. See
[All machines show available while telemetry is stale](guide:all-machines-available-telemetry-stale).

## Steps {#steps}

1. Watch one full attempt yourself and write down the exact wording the kiosk
   showed after the machine was chosen. *Machine start failed* and a normal
   start message lead to completely different causes.
2. Open `/dev/admin` and read the Overview panel. Note **Backend relay** and
   **Telemetry**. If backend relay is disabled, the backend is not sending power
   commands at all — stop here and escalate rather than switching it on
   yourself, because it makes the backend drive real hardware.
3. Go to Diagnostics, Live readings, and find the machine. Note **Run state**,
   **Pending start**, **Last read**, the value and the band text.
4. Repeat one start attempt while you watch that card. A machine that really
   gets power shows the value climbing within a few seconds.
5. If the value climbs but the band text never says *at or above ON threshold*,
   or **Above for** never reaches the ON confirm time, the run is happening but
   cannot be confirmed. Do not change thresholds in the middle of an incident;
   threshold tuning is its own procedure and it is easy to make availability
   worse.
6. Open Diagnostics, Change history, and look for a recent change to a runtime
   or hardware setting. A start problem that began today usually began with a
   change today.
7. Wait for the reservation to expire, or let it run out, before the next test.
   A machine that is still holding a pending start cannot be chosen again.

## If this did not fix it {#escalate}

Escalate when relay control is off and switching it on is not your decision,
when the reading never moves at all, or when the kiosk reports *Machine start
failed* repeatedly.

Use **Copy support report** at the bottom of this guide and send it together with: which machine, the exact
kiosk wording, roughly how many seconds passed before the kiosk reset, and
whether the reading moved at all during the attempt.
