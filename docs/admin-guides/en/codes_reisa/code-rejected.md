---
id: code-rejected
locale: en
canonical: true
title: "Code is rejected or the scan does not advance"
summary: "The kiosk reacts to the scan with an error and goes back to the ready screen."
category: codes_reisa
kind: troubleshooting
risk: medium
status: published
last_reviewed: 2026-09-03
common_problem_rank: 4
related_guides:
  - scanner-not-scanning
  - machine-does-not-start
  - reisa-configuration
related_settings:
  - provider_default
  - provider_reisa_enabled
  - reisa_base_url
  - reisa_bearer_token
  - reisa_connect_timeout_ms
  - reisa_read_timeout_ms
  - code_expiration_days
diagnostics:
  - core
  - kiosk.state
  - settings.provider
  - provider.reisa
search_aliases:
  - code expired or invalid
  - code does not work
  - qr code refused
  - system busy message
  - no remaining uses
checks:
  - id: error-message-shown
    question: "Did the kiosk show an error, or did nothing happen at all?"
    look_for: "The kiosk screen during the scan."
    expected: "An error message. Complete silence is a scanner problem, not a code problem."
    problem_guide: scanner-not-scanning
  - id: scan-log-row
    question: "What does the scan log say about that scan?"
    look_for: "Diagnostics, Scan log, the newest row, Result and Details."
    expected: "A row with result invalid and a details value naming the reason."
    route: diagnostics
  - id: kiosk-was-ready
    question: "Was the kiosk on its ready screen when the code was scanned?"
    look_for: "Overview, Current UI state, and the wording on the kiosk screen."
    expected: "waiting_for_code. Scans sent in any other state are refused as busy."
    route: overview
    diagnostics: kiosk.state
  - id: active-provider
    question: "Which provider is validating codes right now?"
    look_for: "Overview, Provider and Reisa enabled."
    expected: "The provider you expect for this site."
    route: overview
    diagnostics: settings.provider
  - id: another-code-works
    question: "Does a different code work at the same kiosk?"
    look_for: "The kiosk screen after scanning a second, known-good code."
    expected: "It advances to machine selection, which narrows the fault to the first code."
---

## When to use this {#when-to-use}

Use this guide when the kiosk clearly reacts to a scan — a short error message
appears and the screen returns to the ready state a few seconds later — but the
customer never gets to choose a machine.

If nothing at all happens when the code is scanned, this is the wrong guide:
read [Scanner is not scanning](guide:scanner-not-scanning).

The wording on the screen is the single most useful thing you can write down.
*Code expired or invalid*, *No remaining uses*, *Missing code* and *System busy*
come from four different places in the flow.

## Possible causes {#causes}

**The code is used up or expired.** With local codes, a code is refused once its
uses are spent or its expiry has passed. The last use also sets an expiry a day
out, so a fully used code stays refused afterwards. `code_expiration_days` only
affects codes created after it was changed, so it never explains an old code
that stopped working today.

**The entitlement has no uses left.** When Reisa is the active provider, the
kiosk refuses a scan whose remaining uses have reached zero, with a message
saying so. This is the normal outcome of a code that has already been used the
paid number of times.

**The kiosk was not ready.** Scans are only accepted on the ready screen. A scan
sent while the previous customer is still choosing a machine, or while an error
is being shown, is refused as busy and recorded with a busy reason. Two people
scanning within a few seconds of each other produce this reliably.

**The provider could not be reached or refused the lookup.** In Reisa mode the
kiosk asks the provider about every scan. A network problem, a timeout or a
rejected request all surface as an error on the kiosk and a failed lookup in the
scan log.

**The wrong provider is active.** Codes are validated locally unless
`provider_default` is Reisa **and** `provider_reisa_enabled` is on. If the site
sells Reisa entitlements but the kiosk is validating locally, every real code is
unknown to it and every scan is refused.

## Steps {#steps}

1. Write down the exact message the kiosk showed, and roughly when.
2. Open `/dev/admin`, go to Diagnostics, **Scan log**, and find that scan. The
   **Details** column carries the reason the backend recorded — a busy state, an
   invalid or expired code, or a failed provider lookup.
3. Read Overview: **Provider** and **Reisa enabled**. Compare with what this site
   is supposed to sell. A mismatch here explains every code failing at once.
4. If the details say the kiosk was busy, watch the kiosk for a moment. The
   fix is timing, not the code: let the screen return to ready before scanning.
   A kiosk that never returns to ready is a different problem — see
   [Machine does not start after selection](guide:machine-does-not-start).
5. Scan a second code you know is good. One code failing while others work is a
   customer entitlement question, not a kiosk fault.
6. If every code fails and the provider is Reisa, treat it as a provider or
   network incident rather than a code incident and escalate. Reisa settings are
   high risk and the base URL and token are not something to experiment with
   during service.

> [!NOTE]
> The panel and the support report only ever record **whether** the Reisa URL and
> token are configured, never their values. Do not read out or forward a token
> when reporting this problem.

## If this did not fix it {#escalate}

Escalate when every code is refused, when the scan log shows failed provider
lookups, or when a customer insists a code has unused washes left.

Use **Copy support report** at the bottom of this guide and send it with: the
exact kiosk message, the Details value from the scan log, whether one code or
all codes are affected, and which provider Overview reported.
