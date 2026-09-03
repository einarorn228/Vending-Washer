---
id: machine-unavailable
locale: en
canonical: true
title: "Machine shows unavailable while it is idle"
summary: "One machine stays marked In use on the kiosk even though nobody is using it."
category: machines_telemetry
kind: troubleshooting
risk: medium
status: published
last_reviewed: 2026-09-03
common_problem_rank: 1
related_guides:
  - machine-does-not-start
  - all-machines-available-telemetry-stale
related_settings:
  - telemetry_enabled
  - machine_reservation_minutes
  - telemetry_http_timeout_sec
diagnostics:
  - machine.identity
  - machine.telemetry
  - machine.thresholds
  - settings.telemetry
search_aliases:
  - machine stuck in use
  - washer shows busy but is empty
  - cannot choose machine
  - machine card greyed out
checks:
  - id: machine-run-state
    question: "What run state does the backend hold for this machine?"
    look_for: "Diagnostics, Live readings, Run state on that machine's card."
    expected: "available for an idle machine. in_use or offline explains the kiosk badge."
    route: diagnostics
    diagnostics: machine.identity
  - id: machine-pending-start
    question: "Is the machine still holding a pending start from an earlier selection?"
    look_for: "Diagnostics, Live readings, Pending start."
    expected: "No. Yes means the machine is reserved and the reservation has not expired yet."
    route: diagnostics
    diagnostics: machine.identity
    problem_guide: machine-does-not-start
  - id: machine-last-reading
    question: "Is the machine still being read, and what is the value?"
    look_for: "Diagnostics, Live readings, the value and Last read."
    expected: "A number, refreshed about as often as the machine's poll interval."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: machine-band
    question: "Where does the reading sit against the thresholds?"
    look_for: "Diagnostics, Live readings, the band text under the value."
    expected: "at or below OFF threshold for an idle machine."
    route: diagnostics
    diagnostics: machine.thresholds
  - id: telemetry-polling-on
    question: "Is telemetry polling running?"
    look_for: "The warning banner at the top of Diagnostics, and Telemetry on Overview."
    expected: "Enabled, with no telemetry-off banner."
    route: diagnostics
    diagnostics: settings.telemetry
    problem_guide: all-machines-available-telemetry-stale
---

## When to use this {#when-to-use}

Use this guide when **one** machine keeps showing as *In use* on the kiosk and
cannot be chosen, while the machine itself is standing idle. The other machines
behave normally.

If instead **every** machine looks free and customers are being sent to machines
that are already running, this is the wrong guide — read
[All machines show available while telemetry is stale](guide:all-machines-available-telemetry-stale).

A machine that has been switched off in the panel does not appear like this at
all: it disappears from the kiosk screen completely rather than showing as busy.

## Possible causes {#causes}

The kiosk marks a machine as choosable only when the backend holds it as
*available* **and** no start is pending on it. Three states produce the badge you
are looking at.

**The machine is still reserved.** When a customer selects a machine, the
backend holds a pending start on it until telemetry confirms the run or the
reservation expires after `machine_reservation_minutes`. A selection that never
turned into a real run therefore blocks the machine for the rest of that window.

**The backend believes the machine is running.** Telemetry marks a machine as
running when its reading sits at or above the ON threshold for the ON confirm
time, and only releases it when the reading sits at or below the OFF threshold
for the OFF confirm time. A machine that keeps drawing more than the OFF
threshold while idle — a standby light, a pump, a heater — never gets released.
The same happens if the reading is stuck between the two thresholds, which is
where nothing changes at all.

**The device stopped answering.** A failed read marks the machine offline, which
also removes it from selection. On the card the value shows as a dash while
**Last read** keeps resetting to a small number: the backend is still reading on
schedule and every attempt is failing. That is a network or device problem, not
a threshold problem. A device that answers too slowly counts as a failed read
once it passes `telemetry_http_timeout_sec`.

## Steps {#steps}

1. Open `/dev/admin`, go to Diagnostics and stay on **Live readings**. Find the
   machine that is wrong.
2. Read the card top to bottom: **Run state**, **Available**, **Pending start**,
   the value, the band text, **Last read**.
3. If **Pending start** is yes, someone selected the machine and the run was
   never confirmed. Wait out the reservation window and watch it clear on its
   own, then read
   [Machine does not start after selection](guide:machine-does-not-start).
4. If **Run state** is `in_use` while the machine is idle, look at the value and
   the band text. A value that sits above the OFF threshold with the machine
   doing nothing means the thresholds no longer match this machine. Note the
   idle value and stop here; changing thresholds is a separate procedure and
   doing it blind can take the machine out of service for real.
5. If the value shows as a dash, the device is not answering. **Last read** will
   still be small, because the backend keeps trying and each attempt fails.
   Check whether other machines on the same device or the same network are also
   affected before you touch anything.
6. Only when **Run state** is `available` *and* **Pending start** is no should
   the kiosk offer the machine. If both of those are true and the kiosk still
   shows it as busy, the kiosk screen is out of date rather than the backend:
   reload the kiosk page and compare again.
7. Note whether the telemetry-off banner is showing at the top of Diagnostics.
   With polling off, whatever state a machine was in when polling stopped is
   frozen in place.

## If this did not fix it {#escalate}

Escalate when the machine has been stuck for longer than one reservation
window with no pending start, when the value never updates, or when an idle
machine genuinely reads above its OFF threshold.

Use **Copy support report** at the bottom of this guide and send it with: which
machine, its Run state and value as you saw them, and whether the machine had
been used shortly before it got stuck.
