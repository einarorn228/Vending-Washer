---
id: kiosk-cannot-reach-backend
locale: en
canonical: true
title: "Kiosk screen is stale or cannot reach the backend"
summary: "The kiosk screen is frozen on one view, or shows a connection banner, while the system itself may be fine."
category: kiosk_display
kind: troubleshooting
risk: medium
status: published
last_reviewed: 2026-09-03
common_problem_rank: 6
related_guides:
  - all-machines-available-telemetry-stale
  - admin-panel-orientation
related_settings:
  - kiosk_poll_interval_ms
  - api_key
diagnostics:
  - core
  - kiosk.state
search_aliases:
  - screen frozen
  - backend connection lost
  - kiosk does not update
  - screen shows old information
checks:
  - id: kiosk-banner-text
    question: "Is there a banner on the kiosk screen, and what does it say?"
    look_for: "The top of the kiosk screen."
    expected: "No banner. A connection banner and a missing-API-key banner mean different things."
  - id: admin-panel-loads
    question: "Does the admin panel load at all from this host?"
    look_for: "Open /dev/admin in a browser."
    expected: "It loads and asks for the login."
    route: overview
    diagnostics: core
  - id: backend-reachable
    question: "Does Overview report the backend as reachable?"
    look_for: "Overview, Backend reachable."
    expected: "yes."
    route: overview
    diagnostics: core
  - id: state-matches-screen
    question: "Does the backend's kiosk state match what the kiosk screen is showing?"
    look_for: "Remote Control, the kiosk state readout, next to the kiosk screen itself."
    expected: "The same state. A difference means the screen is stale, not the backend."
    route: remote_control
    diagnostics: kiosk.state
  - id: screen-follows-after-reload
    question: "Does the kiosk screen start following again after the page is reloaded?"
    look_for: "The kiosk screen for about a minute after a reload."
    expected: "It tracks scans and machine changes again."
---

## When to use this {#when-to-use}

Use this guide when the kiosk screen is not keeping up with reality: it stays on
one screen, shows information you know is out of date, or carries a banner about
the connection to the backend.

There is a short version of this for anyone on site without a login, at the
public help page. This guide is the diagnostic version: it assumes you can open
`/dev/admin` and compare the screen with what the backend actually holds.

Be careful about what you conclude from a stale screen. The machines shown on it
can be wrong for two very different reasons: the screen is not receiving updates,
or the backend's own picture of the machines is stale. The second one is
[All machines show available while telemetry is stale](guide:all-machines-available-telemetry-stale).

## Possible causes {#causes}

**The kiosk page cannot reach the backend.** The screen asks the backend for the
current state about once a second — every `kiosk_poll_interval_ms`, one second
by default. When a request fails, the screen keeps the last state it received
and shows a *Backend connection lost* banner. The picture on screen is then
simply old, not wrong on purpose.

**The browser has no API key.** Every request the kiosk makes carries the API
key. If the browser has none — the usual case being a kiosk page reloaded before
the frontend was restarted with its key in place — the screen shows a banner
saying so instead of the connection banner. Nothing on the kiosk itself can fix
that; it is a maintainer step on the kiosk host.

**The key is present but not accepted.** A key the backend rejects makes the
page reload itself shortly after each attempt, so the screen appears to restart
over and over without ever settling.

**The browser is serving a cached answer.** This is the recorded incident behind
this guide: Chromium held on to a cached response for the state request and the
kiosk sat on an old screen with no banner at all, while the backend was healthy
the whole time. Requests are now made with caching switched off, so this should
not recur — but a screen that is stale with **no** banner is still the shape to
suspect, and a reload settles it.

**The backend is not running.** Then the panel will not load either, and the
kiosk cannot recover on its own.

## Steps {#steps}

1. Look at the kiosk screen and note whether there is a banner and what it says.
   The connection banner and the missing-key banner point at different causes,
   and no banner at all points at the browser rather than the network.
2. Open `/dev/admin` from the kiosk host or another device on the same network.
   If the panel does not load either, this is not a kiosk-screen problem —
   escalate; the backend or the host needs attention.
3. In the panel, read Overview: **Backend reachable** and **Current UI state**.
4. Open Remote Control and compare the kiosk state it reports with what the
   kiosk screen is showing.
   - They agree: the screen is fine and the backend is genuinely sitting in that
     state.
   - They differ: the screen is stale.
5. Reload the kiosk page and watch it for a minute. A stale page that starts
   following again after a reload was a browser problem, and that is worth
   recording even though it is now fixed.
6. If the screen updates but feels sluggish, check `kiosk_poll_interval_ms` in
   Settings, under **Screen Timing**, before assuming a fault. A long interval is a configured choice, not
   a connection failure.
7. Do not type or paste keys into the kiosk browser to get past a missing-key
   banner. Report it instead.

> [!WARNING]
> A stale kiosk screen can show a machine as free when it is not. Until the
> screen is following the backend again, do not let staff or customers decide
> which machine is free from that screen.

## If this did not fix it {#escalate}

Escalate when the panel does not load, when Overview reports the backend as not
reachable, when the missing-key banner is showing, or when the page reloads
itself repeatedly.

Use **Copy support report** at the bottom of this guide and send it with: the
exact banner text, whether `/dev/admin` loaded, what Overview said for Backend
reachable and Current UI state, and whether a reload changed anything.
