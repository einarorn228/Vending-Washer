---
id: admin-access-recovery
locale: en
canonical: true
title: "Admin access and dev/admin panel recovery"
summary: "What to do when nobody can get into /dev/admin any more: the panel switched off, a lost admin password, or a lost API key."
category: admin_recovery
kind: recovery
risk: high
status: published
last_reviewed: 2026-09-03
related_guides:
  - admin-panel-orientation
  - kiosk-cannot-reach-backend
  - settings-requiring-restart
related_settings:
  - dev_admin_enabled
  - admin_username
  - admin_password_hash
  - api_key
  - cors_allowed_origins
diagnostics:
  - core
search_aliases:
  - locked out of the admin panel
  - panel disabled
  - forgot the admin password
  - lost api key
  - cannot log in to dev admin
  - turn the admin panel back on
checks:
  - id: which-lockout
    question: "What exactly does the page show?"
    look_for: "The /dev/admin page: the login form, a panel-disabled message, or nothing loading at all."
    expected: "A login form. A panel-disabled message and a page that does not load are different problems."
    route: overview
    diagnostics: core
  - id: page-loads-at-all
    question: "Does the page load from this device at all?"
    look_for: "Open /dev/admin in a browser on the kiosk host and on one other device."
    expected: "It loads on both. If it loads on neither, this is not a credentials problem."
    route: overview
    diagnostics: core
    problem_guide: kiosk-cannot-reach-backend
  - id: credentials-recorded
    question: "Is there a written record of the admin username and password anywhere?"
    look_for: "Wherever the site keeps its credentials."
    expected: "A record exists. Check it before changing anything on the host."
  - id: host-access-available
    question: "Can somebody reach a terminal on the kiosk host?"
    look_for: "Physical or remote access to the machine the backend runs on."
    expected: "Yes. Every recovery below happens there, not in a browser."
  - id: database-backed-up
    question: "Has the database file been copied before any credential change?"
    look_for: "A dated copy of the database file on the kiosk host."
    expected: "A copy made before the first change."
  - id: one-change-verified
    question: "Was each credential change verified before the next one was made?"
    look_for: "A successful login, or a successful request, after each single change."
    expected: "Yes. Two changes at once cannot be told apart when neither works."
---

## When to use this {#when-to-use}

Use this guide when the `/dev/admin` panel cannot be reached any more: the page
says the panel is disabled, the login is refused, or the API key that clients use
has been lost.

Getting back in happens on the kiosk host, in a terminal, from the repository
root. None of that can be done from a browser — that is deliberate, because the
thing you are recovering is the lock on the browser. Only the last section below,
replacing an API key you already recovered, is done in the panel afterwards.

If the page does not load at all on any device, this is the wrong guide: nothing
here helps when the backend is unreachable. Read
[Kiosk screen is stale or cannot reach the backend](guide:kiosk-cannot-reach-backend)
first, and confirm the backend is running before assuming a credentials problem.

> [!DANGER]
> Change **one** credential at a time and verify it works before touching the
> next. Changing the admin password and the API key in one sitting is the single
> most reliable way to turn a recoverable lockout into an unrecoverable one,
> because when nothing works afterwards there is no way to tell which change broke
> it. Never paste a password or a key into a chat message, a ticket, or a settings
> field in the panel.

> [!WARNING]
> Before the first change, copy the database file on the kiosk host to a dated
> filename. Settings, credentials, machine mapping, codes and the audit trail all
> live in that one file, and a copy taken beforehand is the only way back from a
> mistyped value. If the panel is still reachable at this point, also press
> **Export current config** on the Overview tab and keep the downloaded file; it
> contains the settings and machine mapping, and records only whether each secret
> is set, never its value.

## Possible causes {#causes}

**The panel was switched off.** `dev_admin_enabled` is the backend kill switch.
When it is off, every request the panel makes is refused and the page shows a
panel-disabled message. Turning it off is a one-way door from the browser: the
Danger Zone requires the phrase `DISABLE DEV ADMIN` to be typed exactly, and once
it is off there is no page left to turn it back on from.

**The admin credentials do not match.** The panel is protected by HTTP Basic
authentication against `admin_username` and `admin_password_hash`. The password
itself is never stored — only a hash of it — so a forgotten password cannot be
looked up, only replaced. The same credentials also guard the site's other admin
routes.

**The API key is lost.** `api_key` is what kiosk clients send on every request.
It does not unlock the panel, but without it the kiosk screen cannot talk to the
backend, and the panel's Sensitive Settings section asks for it before it will
rotate a secret.

**The browser is being blocked rather than the credentials refused.**
`cors_allowed_origins` decides which browser origins the backend answers. A wrong
value there stops the panel and the kiosk reaching the backend from a browser
even though the credentials are perfect. It is one of the settings that only
takes effect after a restart, so a bad value saved earlier can appear at the next
restart rather than at the moment it was saved. See
[Settings that need a restart](guide:settings-requiring-restart).

Repeated wrong passwords do not lock the account or start a waiting period; they
are only counted in the backend's failure metric. If a login is refused, the
credentials really are wrong.

## Steps {#steps}

1. Read the page carefully first. A *panel disabled* message, a refused login and
   a page that does not load are three different problems with three different
   fixes. Try one other device before concluding anything.
2. Look for a written record of the credentials before changing them. A password
   that already exists somewhere is always better than a new one.
3. On the kiosk host, from the repository root, take a dated copy of the database
   file. Do not skip this because the change looks small.
4. Work through only the section below that matches your situation, and verify it
   before starting another one.

### If the panel is switched off

Run this on the kiosk host, from the repository root. It sets the kill switch
back on and nothing else:

```bash
source .venv/bin/activate
python - <<'ENABLE'
from backend.models import Session
from backend.models.setting_model import update_setting_value

session = Session()
try:
    update_setting_value(session, "dev_admin_enabled", "true")
finally:
    session.close()
ENABLE
```

No restart is needed. Reload `/dev/admin` and stop here if you can now log in.
Switch the panel off again the same way, with `"false"` in place of `"true"`,
once the work is finished.

### If the API key is what is missing

```bash
python backend/scripts/get_api_key.py
```

Run this only on the kiosk host, in a session nobody else can see, and clear the
terminal afterwards. The key is a secret: it belongs in the site's credential
store, not in a message or a ticket.

### If the admin password is lost

Before replacing it, test any candidate you found in the site's credential store.
This prompts for the password, prints only yes or no, and never shows the stored
value:

```bash
source .venv/bin/activate
python - <<'CHECK'
import getpass, hashlib
from backend.models import Session
from backend.models.setting_model import get_setting_value

pw = getpass.getpass("Password to test: ")
s = Session()
try:
    print("matches the stored admin password:",
          get_setting_value(s, "admin_password_hash") == hashlib.sha256(pw.encode("utf-8")).hexdigest())
finally:
    s.close()
CHECK
```

If none of them match, set a new password. This prompts for it twice rather than taking it as an
argument, so the password never reaches the shell history:

```bash
source .venv/bin/activate
python - <<'ROTATE'
import getpass, hashlib
from backend.models import Session
from backend.models.setting_model import update_setting_value

pw = getpass.getpass("New admin password: ")
if pw != getpass.getpass("Confirm: "):
    raise SystemExit("passwords did not match; nothing changed")
if len(pw) < 12:
    raise SystemExit("use at least 12 characters; nothing changed")

s = Session()
try:
    update_setting_value(s, "admin_password_hash", hashlib.sha256(pw.encode("utf-8")).hexdigest())
    print("admin_password_hash updated")
finally:
    s.close()
ROTATE
```

Verify immediately, before changing anything else: open `/dev/admin` and log in
with the existing username and the new password. Credential changes take effect
straight away and no restart is involved. Record the new password in the site's
credential store the moment it works.

### If the API key needs replacing rather than recovering

Do that from inside the panel once you are back in: Settings, **Sensitive
Settings**, **Generate New API Key**. It asks for the current API key first, shows
the new value once in a window, and never shows it again — write it down before
closing that window. Every kiosk still using the old key loses access the instant
it is generated, so plan to update them in the same session.

## If this did not fix it {#escalate}

Escalate when there is no terminal access to the kiosk host, when the backend
itself is not running, when the panel still refuses a password that was just set,
or when the page cannot be reached from any device even after the panel is
enabled again. Escalate rather than guessing if `cors_allowed_origins` looks
wrong: repairing it needs a restart, and a second wrong value makes the situation
harder to read.

Once you are back in, use **Copy support report** at the bottom of this guide and
send it with: what the page showed before the recovery, which of the sections
above were used and in what order, whether a copy of the database file was taken
first, and whether the panel was left enabled or switched off again afterwards.
Never include a password, a key or a hash.
