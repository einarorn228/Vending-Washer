---
id: scanner-not-scanning
locale: en
canonical: true
title: "Scanner is not scanning"
summary: "A code is held under the scanner and nothing at all happens on the kiosk screen."
category: scanner
kind: troubleshooting
risk: medium
status: published
last_reviewed: 2026-09-03
common_problem_rank: 5
related_guides:
  - code-rejected
  - admin-panel-orientation
related_settings:
  - serial_port
  - serial_baudrate
  - scan_timeout
diagnostics:
  - scanner.status
  - settings.scanner
  - kiosk.state
actions:
  - restart_backend
search_aliases:
  - scanner does nothing
  - qr code not read
  - no reaction when scanning
  - scanner light is off
checks:
  - id: scanner-reacts
    question: "Does the scanner itself react when a code is held under it?"
    look_for: "The scanner's own light and beep, not the kiosk screen."
    expected: "It lights up and beeps for each code."
  - id: scanner-available
    question: "Does the backend have the scanner open?"
    look_for: "Overview, Scanner available."
    expected: "yes. no means the serial port could not be opened when the backend started."
    route: overview
    diagnostics: scanner.status
  - id: scanner-port
    question: "Is the configured scanner port the one the scanner is plugged into?"
    look_for: "Overview, Scanner port."
    expected: "The port the scanner presents on this host, normally /dev/ttyACM0."
    route: overview
    diagnostics: scanner.status
  - id: scan-log-row
    question: "Does a new row appear in the scan log when you scan?"
    look_for: "Diagnostics, Scan log, the newest row and its Details column."
    expected: "No new row at all means the scan never reached the kiosk flow."
    route: diagnostics
    problem_guide: code-rejected
  - id: recent-scanner-setting-change
    question: "Were the scanner settings changed without a restart afterwards?"
    look_for: "Diagnostics, Change history, and the restart banner at the top of the panel."
    expected: "No pending scanner change. Saved scanner settings only apply after a restart."
    route: diagnostics
    diagnostics: settings.scanner
---

## When to use this {#when-to-use}

Use this guide when a customer holds a code under the scanner and **nothing
happens**: no machine selection screen, no error, no message.

If the kiosk does react but shows a red error and returns to the ready screen,
the scan reached the system and was refused — read
[Code is rejected or the scan does not advance](guide:code-rejected) instead.
That difference is the fastest split in this whole area: silence points at the
scanner, an error points at the code.

## Possible causes {#causes}

**The backend never opened the scanner.** The serial port is opened once when
the backend starts. If the scanner was unplugged at that moment, or the
configured port was wrong, the reading thread never starts and no scan can
arrive until the backend is restarted. Overview reports this directly as
*Scanner available: no*.

**Scanner settings were changed but not applied.** `serial_port`,
`serial_baudrate` and `scan_timeout` are read only when the scanner is opened.
Saving them changes the stored value but not the running scanner, which is why
the panel marks them as needing a restart.

**The code is not a shape the system accepts.** The backend only forwards
strings that look like an entitlement: an eight-character code, a UUID, a
32-character hex string, or a PIN of four to twelve digits. Anything else — a
product barcode, a loyalty card, a torn or misprinted label — is dropped without
a message and without a scan-log row.

**The scanner itself is not reading.** If the scanner does not light up or beep
at all, the problem is in front of the software: power, cable, or the scanner's
own configuration.

## Steps {#steps}

1. Hold a code under the scanner yourself and watch the scanner, not the screen.
   A scanner that does not light up or beep is not reading anything, and no
   setting in the panel will change that.
2. Open `/dev/admin` and read Overview: **Scanner available** and
   **Scanner port**. If Scanner available is *no*, the backend has no scanner
   open and every scan will be silent until that is fixed.
3. Go to Diagnostics, **Scan log**, and scan again with the kiosk on its ready
   screen. Watch for a new row.
   - A new row means the scanner works and the problem is the code itself.
   - No row at all means nothing reached the kiosk flow.
4. Try a code you know is good, for example one you have just scanned
   successfully at another moment. If that one is read and the customer's is
   not, the label is the problem, not the kiosk.
5. Check Diagnostics, **Change history**, for a recent change to a scanner
   setting, and look for the restart banner at the top of the panel. Saved
   scanner settings only take effect once the backend has been restarted on the
   kiosk host; the banner shows whoever does that the exact command.
6. Do not change `serial_port` or `serial_baudrate` to see what happens. A wrong
   port leaves the kiosk with no scanner at all after the next restart, which is
   a worse failure than the one you started with.

## If this did not fix it {#escalate}

Escalate when Scanner available is *no*, when the scanner does not react
physically, or when the scan log stays empty while the scanner beeps normally.

Use **Copy support report** at the bottom of this guide and send it with: what
the scanner did physically, what Overview showed for Scanner available and
Scanner port, whether any row appeared in the scan log, and whether one specific
code or every code is affected.
