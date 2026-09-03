---
id: using-diagnostics
locale: en
canonical: true
title: "Reading Overview and Diagnostics"
summary: "What every field on Overview and in the Diagnostics tab means, and what to collect before escalating."
category: machines_telemetry
kind: concept
risk: low
status: published
last_reviewed: 2026-09-03
related_guides:
  - admin-panel-orientation
  - machine-unavailable
  - all-machines-available-telemetry-stale
  - no-telemetry-reading
  - tune-thresholds
  - settings-requiring-restart
related_settings:
  - telemetry_enabled
  - telemetry_http_timeout_sec
  - log_level
diagnostics:
  - core
  - kiosk.state
  - machine.identity
  - machine.telemetry
  - machine.thresholds
  - machine.mapping
  - settings.telemetry
search_aliases:
  - what does this field mean
  - reading the overview page
  - live readings explained
  - change history
  - support report contents
  - where to look first
---

## What Overview tells you {#overview}

Overview is the whole system in one screen, refreshed every few seconds. It is
the right first look for almost every problem, because it separates "the backend
is unhealthy" from "one machine is unhealthy" in a few lines.

| Field | What it means |
|---|---|
| **Backend reachable** | Whether this page is getting answers from the backend at all. |
| **Dev/admin enabled** | Whether the kill switch for this panel is on. |
| **Provider** | Which provider validates codes: `local` or `reisa`. |
| **Reisa enabled** | Whether the Reisa provider is allowed to be used. |
| **Scanner port** | The serial port the scanner is configured for. This is the saved setting, not proof the running backend opened it. |
| **Scanner available** | Whether the running backend actually opened that port. |
| **Current UI state** | What the kiosk state machine is doing right now. |
| **Button box** | Whether the physical button box input is enabled. |
| **Backend relay** | Whether the backend may send real power commands. Disabled means selections are accepted and nothing is switched on. |
| **Telemetry** | Whether the machines are being read at all. |
| **Configured machines** | How many machines exist in the configuration. |
| **Active in kiosk** | How many of them are offered on the kiosk screen. |
| **Status read at** | When this status was generated. It is produced fresh on every refresh, so it is not a start time and not a health signal. |

Overview also carries **Export current config**, which downloads the current
settings and machine mapping as a JSON file with no raw secrets in it. Use it
before risky changes.

## Live readings {#live-readings}

Diagnostics opens on **Live readings**: one card per machine, refreshed about
once a second. If telemetry polling is off, a red banner at the top says so and
everything below it is frozen.

The large number is the machine's latest reading, and the text beside it says
where that reading sits: *at or above ON threshold*, *between thresholds*, *at or
below OFF threshold*, or *no reading* when the last read failed. The small chart
plots roughly the last two minutes with both thresholds drawn as lines.

| Field | What it means |
|---|---|
| **Run state** | What the backend believes the machine is doing: `available`, `in_use` or `offline`. |
| **Available** | Whether the kiosk may offer it. A machine is only available when its run state is `available` and no start is pending. |
| **Pending start** | Whether a customer has selected it and the run has not been confirmed yet. |
| **Last read** | How long ago the backend last *tried* to read it. It resets even when the read failed. |
| **Above for** | How long the reading has been continuously at or above the ON threshold. |
| **Below for** | How long it has been continuously at or below the OFF threshold. |
| **ON threshold**, **OFF threshold** | This machine's two thresholds. |
| **ON confirm**, **OFF confirm** | How long a reading has to hold before the backend acts on it. |
| **Poll interval** | How often this machine is read. |
| **Device** | The address of the device this machine is read from. |

Two badges sit at the top of each card: whether the machine is `active` or
`inactive` in the kiosk, and which metric source it is read with.

Reading those fields together is what tells the guides apart. A dash with a small
and resetting **Last read** is a failing read; a frozen value with a climbing
**Last read** is polling that has stopped; **Above for** never reaching **ON
confirm** is a threshold that sits too high.

## Scan log, Change history and Metrics {#other-views}

**Scan log** lists recent scans with their result and a details value. It answers
one question precisely: did the scan reach the backend at all? No new row means
the scan never arrived, which is a scanner problem rather than a code problem.

**Change history** is the configuration audit trail: every settings and machine
change made through this panel, with the old and the new value, and badges for
high risk and restart required. Secrets appear by presence only, never by value.
This is the first place to look whenever something worked yesterday and does not
work today. It records what changed, not who changed it.

**Metrics** shows the backend's runtime counters and gauges. The one worth
knowing by name is `uptime_seconds_total`: after a real restart it counts up from
zero again, which is the only dependable way to confirm a restart actually
happened. See [Settings that need a restart](guide:settings-requiring-restart).

## The checklist and the support report {#checklists-and-report}

Most troubleshooting guides carry a short checklist under the text. Each item is
a question with a place to look and what to expect, and you mark it **OK**,
**Problem found**, **Not sure** or **Not checked**. Nothing is calculated from
your answers — the checklist is there so that an interrupted investigation can be
picked up again, and so that the evidence travels with the escalation. *Not sure*
is a genuinely useful answer; do not force it to yes or no.

When an item is marked **Problem found** and the guide names a follow-up guide for
it, a link to that guide appears under the item.

**Copy support report** at the bottom of a guide builds a text report and copies
it to the clipboard. If the browser will not allow the copy, the report appears
in a text box instead so you can select it by hand. The report contains the guide
you were reading and which language you were shown, the kiosk state, the scanner
status, whether the provider's base URL and token are configured, the settings
relevant to that guide, the machine fields the guide declares, and your checklist
answers. It never contains a secret value — only whether each secret is set —
and the fields it may include are fixed by the backend, not chosen by the page.

## What to send when you escalate {#escalate}

Send the support report, and add the things only you can know: what the customer
or the staff member actually saw, at what time, on which machine, whether it has
happened before, and exactly what you changed while investigating. A report
without that context says what the system looked like afterwards, which is rarely
the same as what went wrong.

If a machine is involved, open the guide from that machine's context where you
can, so the report is scoped to it. And if you turned something off to make the
situation safe — relay control especially — say so explicitly, because otherwise
the next person reads a healthy-looking system and cannot see why it is idle.
