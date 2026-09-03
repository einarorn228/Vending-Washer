---
id: tune-thresholds
locale: en
canonical: true
title: "Tuning a machine's ON and OFF thresholds safely"
summary: "How to pick the ON and OFF thresholds and the confirm times for one machine without taking it out of service."
category: machines_telemetry
kind: procedure
risk: medium
status: published
last_reviewed: 2026-09-03
related_guides:
  - machine-unavailable
  - machine-does-not-start
  - all-machines-available-telemetry-stale
  - no-telemetry-reading
  - machine-technical-mapping
related_settings:
  - telemetry_enabled
  - telemetry_http_timeout_sec
diagnostics:
  - machine.identity
  - machine.telemetry
  - machine.thresholds
  - settings.telemetry
search_aliases:
  - threshold too high
  - machine never registers as running
  - machine flips between free and busy
  - on confirm time too short
  - reading does not reach the threshold
checks:
  - id: telemetry-running
    question: "Is telemetry polling running before you start?"
    look_for: "The banner at the top of Diagnostics, and Telemetry on Overview."
    expected: "Enabled, with no telemetry-off banner. With polling off the readings never move and nothing can be tuned."
    route: diagnostics
    diagnostics: settings.telemetry
    problem_guide: all-machines-available-telemetry-stale
  - id: machine-is-polled
    question: "Is this machine actually being read at all?"
    look_for: "Diagnostics, Live readings, the value and Last read on that machine's card."
    expected: "A number that refreshes. A dash means there is no reading to tune against."
    route: diagnostics
    diagnostics: machine.telemetry
    problem_guide: no-telemetry-reading
  - id: idle-value-recorded
    question: "Have you written down what the machine reads when it is standing idle?"
    look_for: "Diagnostics, Live readings, the value and the chart with the machine switched off."
    expected: "A steady idle number, watched for at least a minute."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: running-value-recorded
    question: "Have you written down what it reads across a whole program?"
    look_for: "Diagnostics, Live readings, the chart during a full wash or dry cycle."
    expected: "The lowest value reached while the machine is genuinely running, not just the peak."
    route: diagnostics
    diagnostics: machine.telemetry
  - id: thresholds-ordered
    question: "Is the OFF threshold below the ON threshold, with a clear gap between them?"
    look_for: "Diagnostics, Live readings, ON threshold and OFF threshold on the card."
    expected: "OFF below ON. Nothing in the panel refuses the opposite, and the opposite makes the machine behave unpredictably."
    route: diagnostics
    diagnostics: machine.thresholds
  - id: confirm-windows-reached
    question: "Do Above for and Below for actually reach the confirm times during a real cycle?"
    look_for: "Diagnostics, Live readings, Above for against ON confirm and Below for against OFF confirm."
    expected: "Above for passes ON confirm shortly after the machine starts, Below for passes OFF confirm after it stops."
    route: diagnostics
    diagnostics: machine.thresholds
---

## When to use this {#when-to-use}

Use this procedure when a machine's readings are healthy but the backend draws
the wrong conclusion from them: a running machine is never confirmed as started,
an idle machine is never released, or a machine flips between free and busy in
the middle of a program.

Do not use it as an incident fix. If a machine is stuck right now, read
[Machine shows unavailable while it is idle](guide:machine-unavailable) or
[Machine does not start after selection](guide:machine-does-not-start) first.
Threshold changes take effect within a second or two and there is nothing to
compare against afterwards if you did not record what the machine was doing
before.

If the value is missing altogether rather than wrong, this is the wrong guide:
read [No telemetry reading for one machine](guide:no-telemetry-reading).

## Before you start {#causes}

**How the backend decides a machine is running.** Each machine is read on its own
poll interval. When the reading is at or above the machine's ON threshold and
stays there for the ON confirm time, the backend marks the machine as running and
releases the pending start. When the reading is at or below the OFF threshold and
stays there for the OFF confirm time, the machine goes back to available. A
reading between the two thresholds changes nothing and resets both timers — that
gap is what stops a machine flickering between the two states.

**Where the numbers live.** They are per machine, not global settings. Open the
**Machine Cards** tab, find the machine's row, and press **Advanced / Technical
Mapping**. The drawer holds **On threshold**, **Off threshold**, **On confirm
ms**, **Off confirm ms** and **Poll interval ms**, alongside the hardware mapping
fields described in
[Machine technical mapping](guide:machine-technical-mapping). All five are whole
numbers: thresholds from 0 to 100000, both confirm times from 0 to 60000
milliseconds, and the poll interval from 500 to 60000 milliseconds.

**Where you watch the effect.** Diagnostics, **Live readings**. Each card shows
the current value, the band text under it (*at or above ON threshold*, *between
thresholds*, *at or below OFF threshold*), **Above for**, **Below for**, and the
machine's own **ON threshold**, **OFF threshold**, **ON confirm**, **OFF confirm**
and **Poll interval**. The chart behind them plots roughly the last two minutes of
readings with both thresholds drawn as lines, which is the fastest way to see
whether a threshold sits in the right place.

**What you need before touching anything.** Two recorded numbers for this
machine: what it reads while standing idle, and the *lowest* value it reaches
across a whole program while genuinely running. A threshold picked from a peak
value will drop out during the quiet part of a cycle.

**Two settings that stop this working.** With `telemetry_enabled` off nothing is
read at all and Diagnostics says so in a banner at the top of the tab. And a read
that takes longer than `telemetry_http_timeout_sec` counts as a failed read, which
blanks the value instead of producing a low one — a machine losing readings is not
a machine that needs different thresholds.

> [!WARNING]
> Nothing in the panel checks that the OFF threshold is below the ON threshold.
> Saving them the wrong way round, or equal, leaves the machine with no band
> between them and its behaviour becomes hard to predict. Check the two numbers
> against each other before you save.

## Steps {#steps}

1. Confirm telemetry is running and that this machine has a live value. Note its
   **Poll interval** — everything below happens at that rhythm.
2. With the machine standing idle and switched off, watch Diagnostics for at
   least a minute and write down the idle value and how much it wanders.
3. Run a full program on the machine by hand. Watch the chart for the whole
   cycle and write down the lowest value it reaches while it is running. Note
   how many seconds pass between the machine starting and the value rising.
4. Choose the OFF threshold above the highest idle value you saw, and the ON
   threshold below the lowest running value you saw. Leave a clear gap between
   them. A machine with a standby light, a pump or a heater has an idle value
   well above zero, and the OFF threshold has to clear it or the machine is never
   released.
5. Change **one** value on **one** machine. Open **Advanced / Technical Mapping**
   for that machine, edit the field, tick the acknowledgement box and save. The
   change is recorded in Diagnostics, **Change history**, and applies to the
   running backend within a second or two — no restart.
6. Watch a full cycle again before changing anything else. On the card, **Above
   for** should pass **ON confirm** shortly after the machine really starts, and
   **Below for** should pass **OFF confirm** after it really stops.
7. If the run is confirmed too late, or never: the reading is not holding at or
   above the ON threshold for long enough. Lower the ON threshold towards the
   running value first; shorten **On confirm ms** only if the reading is clearly
   above the threshold and the delay is the problem.
8. If the machine is released in the middle of a program, the reading dips to or
   below the OFF threshold during a quiet phase. Lengthen **Off confirm ms** so a
   short dip is ridden out, or lower the OFF threshold below that dip while
   keeping it above the idle value.
9. If the machine flips repeatedly between free and busy, the two thresholds are
   too close together for how much this machine's reading moves. Widen the gap
   rather than chasing it with confirm times.
10. Write the final numbers down next to the machine's name. **Change history**
    records them too, but a note you can read on the floor is faster.

## If this did not fix it {#escalate}

Escalate when the idle value overlaps the running value so there is no honest gap
to place thresholds in, when the reading is missing rather than wrong, or when
the same machine needs its thresholds moved again a short time later. Repeated
re-tuning usually means the metric being read does not describe this machine
well, which is a mapping question rather than a threshold question.

Use **Copy support report** at the bottom of this guide and send it with: which
machine, the idle and running values you recorded, the thresholds and confirm
times before and after your change, and what the machine did on the cycle you
watched.
