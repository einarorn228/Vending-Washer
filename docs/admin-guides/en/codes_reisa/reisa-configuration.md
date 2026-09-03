---
id: reisa-configuration
locale: en
canonical: true
title: "Reisa connection and configuration"
summary: "How the Reisa provider is selected and configured, what the panel can tell you about it, and how to fall back to local codes safely."
category: codes_reisa
kind: troubleshooting
risk: high
status: published
last_reviewed: 2026-09-03
related_guides:
  - code-rejected
  - scanner-not-scanning
  - admin-panel-orientation
related_settings:
  - provider_default
  - provider_reisa_enabled
  - reisa_base_url
  - reisa_bearer_token
  - reisa_connect_timeout_ms
  - reisa_read_timeout_ms
  - reisa_action_start
  - reisa_action_completion
  - reisa_retry_worker_enabled
  - reisa_retry_worker_interval_sec
  - reisa_retry_worker_batch_size
diagnostics:
  - core
  - kiosk.state
  - settings.provider
  - provider.reisa
search_aliases:
  - reisa is not answering
  - every code is rejected
  - provider settings
  - switch back to local codes
  - reisa token not set
  - reisa base url
checks:
  - id: which-provider-is-active
    question: "Which provider is the backend actually using?"
    look_for: "Overview, Provider and Reisa enabled."
    expected: "Reisa is only used when Provider reads reisa and Reisa enabled reads yes. Otherwise every scan goes to local codes."
    route: overview
    diagnostics: settings.provider
  - id: base-url-and-token-present
    question: "Are the Reisa base URL and token both configured?"
    look_for: "Settings, the Provider / Mode group, Reisa base URL; and Sensitive Settings, Reisa Provider Integration, Current status."
    expected: "A base URL, and Set / masked for the token. Either one missing makes every Reisa scan fail immediately."
    route: settings
    diagnostics: provider.reisa
  - id: failure-shape
    question: "Do codes fail instantly or after a pause?"
    look_for: "The kiosk screen while a known-good code is scanned."
    expected: "An instant refusal points at configuration or authentication; a pause first points at reachability or timeouts."
    route: overview
    diagnostics: kiosk.state
    problem_guide: code-rejected
  - id: scan-log-rows
    question: "What does the scan log record for the failing scans?"
    look_for: "Diagnostics, Scan log, the newest rows, Result and Details."
    expected: "provider_lookup_failed or provider_unauthorized. The reason itself is shown on the kiosk screen, not in this column."
    route: diagnostics
  - id: recent-provider-change
    question: "Was any provider setting changed recently?"
    look_for: "Diagnostics, Change history, rows for provider keys, marked high risk."
    expected: "No provider change just before the failures started."
    route: diagnostics
  - id: all-codes-or-some
    question: "Does every code fail, or only some?"
    look_for: "Two or three codes you know are valid, scanned in a row."
    expected: "All failing points at the connection or the configuration; some failing points at the codes themselves."
    route: diagnostics
---

## When to use this {#when-to-use}

Use this guide when codes validated by Reisa stop working — every code refused,
codes refused only sometimes, or starts that are accepted at the kiosk but never
recorded on the Reisa side. It is also the guide to read before anyone changes a
provider setting.

If a single code is refused while others work, start with
[Code is rejected or the scan does not advance](guide:code-rejected). That guide
covers the scan itself; this one covers the provider behind it.

Everything on this page is high risk. Provider settings decide whether a paying
customer can wash at all, and a change made in the middle of an incident can turn
a partial outage into a complete one.

## Possible causes {#causes}

**Reisa is not actually selected.** The backend uses Reisa only when
`provider_default` is set to `reisa` **and** `provider_reisa_enabled` is on. If
either is not true, every scan is validated against the local codes table
instead, and Reisa-issued codes are simply unknown. Overview shows both as
**Provider** and **Reisa enabled**.

**The base URL or the token is missing.** `reisa_base_url` holds the address the
backend calls; `reisa_bearer_token` holds the credential. If either is empty
every Reisa call fails before it reaches the network, with a message saying so.
Neither value is checked when it is saved, so a wrong base URL looks perfectly
healthy in the panel.

**The token is present but not accepted.** An authentication failure from Reisa
is refused straight away and is never retried, because retrying a rejected
credential cannot succeed.

**Reisa cannot be reached, or is slow.** `reisa_connect_timeout_ms` decides how
long the backend waits while opening the connection, `reisa_read_timeout_ms` how
long it waits for the answer once connected. Too low, and a healthy but slow
provider produces intermittent failures that look exactly like an outage. These
failures are treated as retryable.

**The action identifiers do not match.** `reisa_action_start` and
`reisa_action_completion` are the identifiers sent to Reisa when a run starts and
when it finishes. A wrong value makes Reisa refuse every start, or every
completion, while everything else about the connection is healthy. That is the
shape to suspect when lookups work and only starts or only completions fail.

**Completions are failing and queueing up.** When a completion cannot be
delivered, the session is marked as failed to sync rather than lost. The optional
retry worker picks such jobs up again: `reisa_retry_worker_enabled` turns it on,
`reisa_retry_worker_interval_sec` decides how often it looks for work, and
`reisa_retry_worker_batch_size` how many jobs it takes per pass. It is off by
default, and toggling it applies without a restart.

## Steps {#steps}

1. Read Overview first. **Provider** and **Reisa enabled** together tell you
   whether Reisa is being used at all. If the site should be on Reisa and this
   says otherwise, you have found the fault — but do not change it yet; see the
   warning below.
2. Scan two or three codes you know are good and watch the kiosk wording and the
   timing. An instant refusal is configuration or authentication. A pause and then
   a refusal is reachability or a timeout.
3. Open Diagnostics, **Scan log**. Failing provider scans are recorded with
   result `invalid` and details `provider_lookup_failed` or
   `provider_unauthorized`. The details column names the stage, not the reason —
   the reason is the message shown on the kiosk screen, so note that wording.
4. In Settings, open the **Provider / Mode** group and read the values without
   changing them: base URL, both timeouts, both action identifiers, and the retry
   worker fields. In **Sensitive Settings**, under **Reisa Provider Integration**,
   **Current status** says only *Set / masked* or *Not set*. The token's value is
   never shown anywhere, and you never need it to diagnose this.
5. Open Diagnostics, **Change history**, and look for provider rows. They are
   marked high risk, and a provider problem that started today usually started
   with one of them.
6. If starts are accepted at the kiosk but nothing appears on the Reisa side,
   suspect the action identifiers or completion delivery rather than the
   connection. Collect the evidence and escalate; replaying queued Reisa work in
   bulk is an operator-playbook action that needs the Reisa diagnostics inspected
   first, and it is not something this panel offers.

> [!WARNING]
> Switching `provider_default` back to `local`, or turning `provider_reisa_enabled`
> off, is not a neutral fallback. Every new scan is then validated against the
> local codes table, so customers holding Reisa entitlements cannot start a
> machine at all, and no start or completion reaches Reisa. Runs that were already
> recorded keep the provider they were created with, so work already in flight
> still goes to Reisa. Make this change only as a deliberate decision by whoever
> owns the site's billing, and expect to have to tell customers.

## If this did not fix it {#escalate}

Escalate rather than experimenting whenever the base URL, the token or an action
identifier looks wrong. Rotating the token, editing the base URL and changing the
action identifiers are all high-risk changes that require the current API key or
an explicit acknowledgement, and getting one of them wrong takes every machine
out of service for every customer.

Use **Copy support report** at the bottom of this guide and send it with: the
exact wording the kiosk showed, whether the refusal was instant or delayed,
whether it affects every code, the scan log rows, and anything from **Change
history** around the time the failures began. The report records only whether the
base URL and the token are configured, never their values — that is deliberate,
and it is all anyone needs.
