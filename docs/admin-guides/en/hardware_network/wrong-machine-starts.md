---
id: wrong-machine-starts
locale: en
canonical: true
title: "The wrong physical machine starts"
summary: "A customer chooses one machine on the kiosk and a different machine in the room powers up."
category: hardware_network
kind: troubleshooting
risk: high
status: published
last_reviewed: 2026-09-03
related_guides:
  - machine-technical-mapping
  - machine-does-not-start
  - machine-unavailable
related_settings:
  - backend_relay_enabled
  - telemetry_enabled
  - shelly_http_timeout_sec
diagnostics:
  - kiosk.state
  - machine.identity
  - machine.mapping
  - machine.telemetry
  - settings.relay
search_aliases:
  - another machine turned on
  - wrong washer started
  - button starts the wrong machine
  - machine names are swapped
  - customer got the wrong dryer
checks:
  - id: which-machine-was-chosen
    question: "Which machine did the customer choose, and which one actually moved?"
    look_for: "The kiosk message at the moment of the start, and the machines in the room."
    expected: "The same machine. Write both names down before anything else changes."
    route: overview
    diagnostics: kiosk.state
  - id: relay-control-state
    question: "Is backend relay control still enabled?"
    look_for: "Overview, Backend relay."
    expected: "Disabled once a wrong start is confirmed, so no further start can power a machine."
    route: overview
    diagnostics: settings.relay
  - id: reading-follows-the-name
    question: "When one machine is run by hand, does the reading rise on the card with that machine's name?"
    look_for: "Diagnostics, Live readings, the value on every card while one machine runs."
    expected: "Only the matching card responds."
    route: diagnostics
    diagnostics: machine.telemetry
    problem_guide: machine-technical-mapping
  - id: shared-device-address
    question: "Do two machine cards show the same device address?"
    look_for: "Diagnostics, Live readings, Device on each card."
    expected: "One address per machine, unless the site really does share a device."
    route: diagnostics
    diagnostics: machine.mapping
  - id: recent-mapping-change
    question: "Was a mapping or a machine setting changed recently?"
    look_for: "Diagnostics, Change history, rows marked high risk."
    expected: "No mapping change just before the first wrong start."
    route: diagnostics
  - id: physical-button-mapping
    question: "If the site uses the physical buttons, does each button select the machine printed next to it?"
    look_for: "Press each button and read the kiosk screen."
    expected: "The name on the screen matches the label on the button."

---

## When to use this {#when-to-use}

Use this guide the moment a customer chooses one machine on the kiosk and a
different machine in the room powers up, or a physical button selects a machine
other than the one it is labelled with.

Treat this as a safety issue rather than a configuration annoyance. A machine
that starts unexpectedly can start with its door open, with somebody's laundry
in it, or with nobody expecting it.

If instead the chosen machine simply never runs, this is the wrong guide:
[Machine does not start after selection](guide:machine-does-not-start).

## Possible causes {#causes}

**The two cards are pointed at each other's devices.** The card carries a name;
the device it points at carries the address the power command goes to. If two
cards are swapped, everything else works perfectly and the wrong machine gets
power every single time. This is the most common shape and the easiest to
confirm.

**The relay channel is wrong.** One device can switch more than one output. A
card pointing at the right device but the wrong channel powers whatever is wired
to that channel, which may be the machine next to it.

**A device address has been reused or has moved.** If a device is replaced, or
the network hands out a different address than the one recorded, the panel's
stored address may now belong to a different device. Nothing warns you: the
command simply succeeds against the wrong hardware.

**The physical button index is wrong.** The i4 button index decides which machine
a physical button selects. A wrong index sends the customer's choice to a
different machine before the relay is ever involved — the kiosk itself will name
the machine it is starting, which is how you tell the two apart.

**Only the label is wrong.** If the card's display name or short label was
edited, the customer is told the wrong name while the mapping underneath is
correct. Less dangerous, but it produces exactly the same complaint, and it is
worth ruling out early because it is the one cause with a harmless fix.

## Steps {#steps}

1. Write down which machine was chosen on the screen and which one actually
   started, with the time. You will not be able to reconstruct this later.
2. Stop further starts. In Settings, under **Shelly / Runtime Toggles**, turn
   **Backend relay control enabled** off. The backend then sends no power command
   to any machine. Confirm it on Overview: **Backend relay** should read
   *disabled*.
3. Tell staff what that means for customers. The kiosk keeps accepting scans and
   keeps reserving machines, but nothing powers on, and a reserved machine cannot
   be chosen again until its reservation runs out. Serve customers manually until
   the mapping is fixed.
4. Check whether this is only a naming problem. In Diagnostics, **Live readings**,
   run each machine by hand for a few seconds and watch which card's value rises.
   If the reading follows the right name every time, the mapping is sound and only
   the label or the button index is wrong.
5. Compare the **Device** address shown on each card. Two cards showing one
   address explains a pair of machines behaving as one.
6. Open Diagnostics, **Change history**, and look for high-risk rows from just
   before the first wrong start. A mapping that used to be right and is now wrong
   almost always has a row here.
7. If the site uses the physical buttons, press each one and read the name the
   kiosk shows. A mismatch there is an I4 button index problem and does not
   involve the relays at all.
8. Correct the mapping only when you know what the right values are, one machine
   at a time, following
   [Machine technical mapping](guide:machine-technical-mapping). Re-verify with
   the reading test before turning relay control back on.
9. Turn **Backend relay control enabled** back on only when the mapping has been
   verified and somebody can watch the machines during the first live start.

> [!WARNING]
> Before you change any mapping, press **Export current config** on the Overview
> tab and write down the values you are about to edit. The export is a JSON file
> of settings, machines, devices, machine configs and the card layout, with no raw
> secrets in it. There is no import in the panel, so it is a record to retype from
> rather than an undo button, and it is the only cheap way back to a mapping that
> at least worked for the other machines.

## If this did not fix it {#escalate}

Escalate, and leave relay control off, when the correct mapping is not known,
when a device answers at an address that is supposed to belong to another
machine, when two machines cannot be separated because they share a device, or
when the mapping is right and the wrong machine still moves. The last one means
the wiring does not match the configuration, and only somebody who can inspect
the installation can settle it.

Use **Copy support report** at the bottom of this guide and send it with: the
machine chosen, the machine that started, the time, whether relay control has
been turned off, the device address on each card, and which card responded when
you ran each machine by hand.
