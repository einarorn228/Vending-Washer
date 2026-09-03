---
id: machine-technical-mapping
locale: en
canonical: true
title: "Machine technical mapping: Shelly IP, relay channel, I4 button"
summary: "How a machine card is tied to a physical device, and how to change or verify that mapping without starting the wrong machine."
category: hardware_network
kind: procedure
risk: high
status: published
last_reviewed: 2026-09-03
related_guides:
  - wrong-machine-starts
  - machine-does-not-start
  - machine-unavailable
  - no-telemetry-reading
  - tune-thresholds
  - admin-panel-orientation
related_settings:
  - backend_relay_enabled
  - telemetry_enabled
  - shelly_http_timeout_sec
  - telemetry_http_timeout_sec
diagnostics:
  - machine.identity
  - machine.mapping
  - machine.telemetry
  - machine.thresholds
  - settings.relay
search_aliases:
  - shelly ip address for a machine
  - relay channel setting
  - i4 button does the wrong thing
  - which device belongs to which machine
  - advanced technical mapping
checks:
  - id: current-mapping-recorded
    question: "Have you recorded the mapping as it is right now, before changing anything?"
    look_for: "Overview, Export current config, plus the values in the Advanced / Technical Mapping drawer."
    expected: "An exported file and a written note of the fields you are about to change."
    route: overview
    diagnostics: machine.mapping
  - id: device-address-matches
    question: "Does the device address on the machine's card match the device you believe it is?"
    look_for: "Diagnostics, Live readings, Device on that machine's card."
    expected: "The address of the device fitted to that physical machine."
    route: diagnostics
    diagnostics: machine.mapping
  - id: telemetry-follows-the-right-machine
    question: "When you run one machine by hand, does the reading rise on that machine's card and no other?"
    look_for: "Diagnostics, Live readings, the value and chart on every card while one machine runs."
    expected: "Exactly one card responds. Two cards moving together means they share a device."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: button-index-unique
    question: "Does each active machine have its own I4 button index?"
    look_for: "Machine Cards, each machine's Advanced / Technical Mapping, I4 button index."
    expected: "No two active machines share an index. The panel refuses a duplicate."
    route: machines
    diagnostics: machine.mapping
  - id: relay-dry-run
    question: "Was the first start after the change made with backend relay control off?"
    look_for: "Overview, Backend relay, before the test start."
    expected: "Disabled for the dry run, so a wrong mapping cannot power a machine."
    route: overview
    diagnostics: settings.relay
  - id: one-machine-changed
    question: "Was only one machine's mapping changed in this session?"
    look_for: "Diagnostics, Change history, the rows since you started."
    expected: "Rows for one machine only."
    route: diagnostics
---

## When to use this {#when-to-use}

Use this procedure when a machine card has to be pointed at a different device,
or when you need to check that the card in the panel really describes the
machine standing on the floor. That happens after a device is replaced, after a
device's address changes, and whenever the wrong machine has started.

If a wrong machine has already started for a customer, deal with that first:
[The wrong physical machine starts](guide:wrong-machine-starts).

This is the highest-consequence screen in the panel. A wrong value here does not
show up as an error message; it shows up as power going to a machine somebody is
standing in front of.

> [!WARNING]
> Record the current mapping before you change anything. Press **Export current
> config** on the Overview tab: it downloads a JSON file containing the settings,
> machines, devices, machine configs and the kiosk card layout, with no raw
> secrets in it — only whether each secret is set. Then write down, or photograph,
> the values shown in the **Advanced / Technical Mapping** drawer for the machine
> you are about to edit. The panel has **no config import**, so that export is a
> record to retype from, not a restore button. A full rollback means restoring the
> database file on the kiosk host, which also rolls back codes, sessions and the
> audit trail — that is a maintainer step, not an operator one.

## Before you start {#causes}

**What a machine card is made of.** A machine card is a name and a layout entry
pointing at a UNI device row. The device carries the address the backend talks
to, which relay output it switches, and how a reading is taken from it. The
machine carries which i4 button selects it, whether it is shown on the kiosk, and
its own thresholds.

**The fields in the drawer.** Open the **Machine Cards** tab, find the machine's
row, and press **Advanced / Technical Mapping**:

| Field | What it controls |
|---|---|
| **Shelly IP** | The address of the UNI device this machine is read from and powered through. An IPv4 address or a hostname. |
| **Relay channel** | Which output on that device is switched when the machine is started, 0 to 3. |
| **I4 button index** | Which physical button on the i4 input device selects this machine, 0 to 15, or blank for none. |
| **Metric source** | How a reading is taken from the device: `voltage`, `power`, `digital`, or `none` to stop polling this machine. |
| **On threshold**, **Off threshold**, **On confirm ms**, **Off confirm ms**, **Poll interval ms** | How a reading is turned into *running* or *idle*. Choosing these is a procedure of its own; do not change them in the same sitting as an address or a channel. |

Above the editable fields the drawer shows **Internal key**, **Database ID**,
**UNI device** and **I4 device**, which are read-only and are how you confirm you
have the machine you think you have.

**Two things that surprise people.** The address and the relay channel are stored
on the *device*, not on the card. If two machine cards point at the same device,
changing either of those on one card moves both. And the I4 button index has to
be unique among machines that are active in the kiosk — the panel refuses a
duplicate, including two cards moved onto the same index in a single save.

**Nothing here autosaves.** The save button stays locked until the
acknowledgement box is ticked, and every change is written to Diagnostics,
**Change history**, marked high risk.

**The two switches that decide what a test does.** With `backend_relay_enabled`
off the backend sends no power command at all, so a start attempt exercises the
whole flow without moving any hardware — that is the safe way to make a first
test after an edit. With `telemetry_enabled` on you can verify the reading side
without any relay command at all, simply by running a machine by hand and
watching which card responds. `shelly_http_timeout_sec` and
`telemetry_http_timeout_sec` decide how long the backend waits for that device
before treating the command or the read as failed; a device at the wrong address
usually shows up as those failures.

## Steps {#steps}

1. Export the config from Overview and write down the current values in the
   drawer for the machine you are about to change. Do this even for a change you
   are sure about.
2. Verify the reading side first, because it costs nothing: with
   `telemetry_enabled` on, run one machine by hand and watch Diagnostics, **Live
   readings**. Exactly one card's value should rise. Note the **Device** address
   shown on that card.
3. Repeat for each machine, one at a time. Two cards that move together share a
   device; a machine that never responds is either at the wrong address or has
   the wrong **Metric source**. Write the real, observed mapping down before you
   edit anything.
4. Change **one** field on **one** machine. Open **Advanced / Technical Mapping**,
   edit it, tick the acknowledgement box, and save.
5. Verify the reading side again exactly as in step 2. If the card you edited now
   follows the right machine, the address and metric source are right.
6. Only then test the power side, and only when you can see the machines. Check
   **Backend relay** on Overview. With it disabled, run a start attempt: the
   kiosk should reach its start message and no machine should move. That proves
   the card and the flow without any risk. The machine stays reserved until the
   reservation window runs out, so leave it alone until it clears rather than
   testing the same machine twice in a row.
7. When a live test is genuinely needed, do it with staff watching every machine
   in the room and nobody in front of them, and stop at the first start. If the
   wrong machine moves, go straight to
   [The wrong physical machine starts](guide:wrong-machine-starts).
8. Re-check the I4 button index if the site uses the physical buttons: press each
   button and confirm the kiosk selects the machine printed next to it.
9. Leave the thresholds alone in this session. Tuning them needs a full cycle of
   observation and mixing it with a mapping change makes both impossible to
   judge.

## If this did not fix it {#escalate}

Escalate before making a second mapping change if the first one did not behave as
expected. Escalate immediately if a machine's address is answering but the
readings clearly belong to a different machine, if two cards cannot be separated
because they share one device, or if a device has to be replaced or re-addressed.
Those are wiring and network changes, not panel changes.

Use **Copy support report** at the bottom of this guide and send it with: which
machine you were editing, the exported config file, the values before and after,
which cards responded when you ran each machine by hand, and whether **Backend
relay** was enabled during any test.
