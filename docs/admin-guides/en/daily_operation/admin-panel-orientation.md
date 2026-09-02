---
id: admin-panel-orientation
locale: en
canonical: true
title: Admin panel orientation
summary: What the /dev/admin beta panel is for and what is safe to touch in it.
category: daily_operation
kind: concept
risk: low
status: published
last_reviewed: 2026-09-02
---

## What this panel is for {#purpose}

The dev/admin panel (`/dev/admin`) is a beta control surface for the kiosk backend.
It brings together four areas in one place: settings editing, machine card layout
management, diagnostics, and a Remote Control panel for exercising the kiosk state
machine without touching the physical hardware.

The panel sits behind HTTP Basic auth using the same admin credentials as the rest
of the admin surface, plus a separate kill switch setting that must be enabled
before the panel unlocks at all.

## What is safe to change {#safe-changes}

Most settings edits made from this panel take effect immediately and are safe to
try, revert, and try again. Machine card layout changes only affect how machines
are presented on the kiosk screen and do not change any hardware behaviour.

Some settings are marked higher risk in the catalog because they affect relay
control or authentication. Read a setting's description in the panel before
changing it, and change one setting at a time so the effect of each change is
easy to see.

## Where to look next {#next-steps}

Use the Diagnostics panel to check the current health of a machine or the scanner
before making a change. Use the Remote Control panel to walk the kiosk state
machine through a scan and start cycle when you want to see the effect of a
setting change without waiting for a real customer to scan a code.
