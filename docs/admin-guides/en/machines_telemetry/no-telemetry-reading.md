---
id: no-telemetry-reading
locale: en
canonical: true
title: "No telemetry reading for one machine"
summary: "One machine's live value is missing or its device stopped answering, while the other machines are read normally."
category: machines_telemetry
kind: troubleshooting
risk: medium
status: published
last_reviewed: 2026-09-03
related_guides:
  - machine-unavailable
  - all-machines-available-telemetry-stale
  - machine-technical-mapping
  - tune-thresholds
related_settings:
  - telemetry_enabled
  - telemetry_http_timeout_sec
diagnostics:
  - machine.identity
  - machine.telemetry
  - machine.mapping
  - settings.telemetry
search_aliases:
  - no reading for a machine
  - device offline
  - value shows a dash
  - machine stopped reporting
  - telemetry read fails
checks:
  - id: only-one-machine
    question: "Is it only this machine, or are all of them affected?"
    look_for: "Diagnostics, Live readings, the value on every card."
    expected: "The others have live values. If every machine is affected this is the wrong guide."
    route: diagnostics
    diagnostics: machine.telemetry
    problem_guide: all-machines-available-telemetry-stale
  - id: run-state-offline
    question: "What run state and value does the machine show?"
    look_for: "Diagnostics, Live readings, Run state and the value on that card."
    expected: "A failed read shows a dash for the value, no reading under it, and run state offline."
    route: diagnostics
    diagnostics: machine.identity
  - id: last-read-behaviour
    question: "Is Last read still resetting to a small number?"
    look_for: "Diagnostics, Live readings, Last read on that card."
    expected: "Small and resetting means the backend is still trying and each attempt fails. Climbing means it is not being read at all."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: metric-source-set
    question: "What metric source is this machine configured with?"
    look_for: "Machine Cards, the machine's Advanced / Technical Mapping, Metric source."
    expected: "voltage, power or digital, matching what this device actually provides. none means the machine is never polled."
    route: machines
    diagnostics: machine.mapping
    problem_guide: machine-technical-mapping
  - id: device-address
    question: "Is the device address on the card the address this device really has?"
    look_for: "Diagnostics, Live readings, Device on that card."
    expected: "The address of the device fitted to this machine."
    route: diagnostics
    diagnostics: machine.mapping
  - id: shared-device-or-network
    question: "Are other devices on the same network segment also failing?"
    look_for: "Diagnostics, Live readings, the values on every card, and whether any share the same address."
    expected: "Only this device affected. Several at once points at the network rather than the device."
    route: diagnostics
    diagnostics: machine.telemetry
---

## When to use this {#when-to-use}

Use this guide when **one** machine has no live reading: its value shows as a
dash with *no reading* under it, or its run state has gone to `offline`, while
the other machines are read normally.

If **every** machine has stopped updating, this is the wrong guide — read
[All machines show available while telemetry is stale](guide:all-machines-available-telemetry-stale).
That one is about polling having stopped, and its dangerous symptom is the
opposite: everything looks free.

The visible consequence here is the reverse. A failed read marks the machine
offline, and an offline machine cannot be chosen on the kiosk, so customers see
it as busy. If that is the complaint you were given, read
[Machine shows unavailable while it is idle](guide:machine-unavailable)
alongside this guide.

## Possible causes {#causes}

**The device is not answering.** Every read is an HTTP request to the device at
the address held on the machine's card. If the device is switched off, has moved
to a different address, or cannot be reached across the network, the read fails,
the value is blanked and the machine is marked offline. The backend keeps trying
on the machine's own poll interval, so **Last read** stays small and keeps
resetting: it is the time since the last *attempt*, not since the last successful
value.

**The device answers too slowly.** A read that has not finished within
`telemetry_http_timeout_sec` counts as a failed read, and produces exactly the
same symptom as a device that is switched off. On a busy or noisy network a
device can be alive and still time out repeatedly.

**The metric source does not match the device.** The metric source decides how a
reading is taken. `voltage`, `power` and `digital` each read the device in a
different way, and a device that does not expose the one selected returns
nothing, which is counted as a failed read. There is one value in the dropdown
the backend has no reader for at all — `pulse`. A machine set to `pulse` never
produces a reading, no matter how healthy the device is.

**The machine is not being polled at all.** Two configurations remove a machine
from the poll loop completely: a metric source of `none`, and a card that is not
**Active in kiosk**. Neither is a fault; both look like a machine that simply
never gets a value. In that case **Last read** climbs instead of resetting,
because there is no attempt being made.

**Telemetry polling is off entirely.** With `telemetry_enabled` off, nothing is
read. Diagnostics says so in a banner at the top of the tab, and the effect is
system-wide rather than limited to one machine.

## Steps {#steps}

1. Open `/dev/admin`, go to Diagnostics and stay on **Live readings**. Confirm
   the other machines have live values. If none of them do, switch guides.
2. On the affected card, read **Run state**, the value, the band text and **Last
   read** together. `offline` with a dash and a small, resetting **Last read** is
   a failing read. A climbing **Last read** means the machine is not being polled
   at all, which is a configuration question rather than a device fault.
3. Note the **Device** address on that card and check whether any other card
   shows the same address. If two machines share a device, they fail together and
   the problem is one device, not two machines.
4. Check whether other devices are failing at the same time. Several at once is a
   network problem; one alone is that device, its power, or its address.
5. Open Diagnostics, **Change history**, and look for a recent change to this
   machine or to a hardware timing setting. A machine that stopped reporting today
   often stopped because something was changed today.
6. Look at the machine's **Metric source** in **Advanced / Technical Mapping**.
   If it reads `none`, the machine is deliberately not polled. If it reads
   `pulse`, that is the cause on its own: no reading can be produced. Do not
   change the field yourself unless you know which metric this device provides —
   it is part of the machine's mapping, covered in
   [Machine technical mapping](guide:machine-technical-mapping).
7. If reads fail only intermittently and the network is known to be slow,
   `telemetry_http_timeout_sec` is the setting that decides how patient the
   backend is. Raising it is a considered change, not an incident reflex, and it
   makes every failing read take longer before it is given up on.
8. While the machine is offline, tell staff it cannot be chosen on the kiosk. It
   is not stuck in a run; it simply cannot be offered until it answers again.

## If this did not fix it {#escalate}

Escalate when the device does not answer at all, when its address appears to have
changed, when several devices fail together, or when the machine's metric source
does not match what the device provides. Those are network, hardware and mapping
changes rather than panel work.

Use **Copy support report** at the bottom of this guide and send it with: which
machine, its run state and **Last read** as you saw them, the device address on
the card, whether any other machine is affected, and anything in **Change
history** from around the time the readings stopped.
