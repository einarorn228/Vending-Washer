# Current state

**Date:** 2026-09-04
**Branch:** `help-hub`
**Measured against:** the working tree of the commit that adds this file — i.e. the tip
of the Task 18 documentation work on `help-hub`, **not** an earlier commit.
**Baseline for comparison:** `d9f6958`
(`d9f695895c3b63dd2724ea2609785103417e2946`, *docs(help): record Task 17 corrections in
the plan*) — the last commit before the Task 18 documentation work began.

Every number below was produced by a command run against this repository and this
machine on the date above. Each section names the command, so the next reader can
re-run it and see whether the fact still holds. **Nothing here was copied from another
document.** Where a document elsewhere disagrees, the command output wins.

The distinction between the two commits above matters for exactly one section: the
Task 18 commits added compiler tests, so the **test counts are HEAD counts, not
`d9f6958` counts** — the [Tests](#tests) section gives both. Every other repository fact
here (the route surface, the Help corpus, what is not implemented) is identical at both
commits; the route count was re-checked at `d9f6958` in a detached worktree and is the
same 44.

Two kinds of fact are mixed here and are labelled: **repository** facts (true for
anyone who checks out this branch) and **this machine** facts (the operator's live
`codes.db` on the kiosk host, which will differ on another install).

> [!NOTE]
> This file goes stale by design. Re-run the commands rather than trusting the numbers
> when the date above is not recent.

## Revision

```bash
git rev-parse HEAD; git rev-parse --abbrev-ref HEAD; git log -1 --format='%H %ad %s' --date=iso
```

Run it: it prints the commit this file's measurements describe. The output recorded at
the time of writing was the **baseline** commit, before the Task 18 documentation work
was committed on top of it:

```
d9f695895c3b63dd2724ea2609785103417e2946
help-hub
d9f695895c3b63dd2724ea2609785103417e2946 2026-09-04 10:48:46 +0000 docs(help): record Task 17 corrections in the plan
```

That baseline is what the "at `d9f6958`" column below compares against. Everything else
in this file describes the working tree as it stands at HEAD.

Toolchain on this machine (`python --version`, `node --version`, `npm --version`):
Python 3.11.2, Node v20.20.2, npm 10.8.2.

## Tests — repository {#tests}

```bash
source .venv/bin/activate
python -m pytest backend/tests/ -q
python -m unittest discover -s backend/tests -t .
cd frontend && node --test src/dev-admin/help/
```

**These are HEAD counts.** They include the compiler tests added alongside the Help
authoring guide, so they are higher than the same commands give at the `d9f6958`
baseline:

| Runner | HEAD | at `d9f6958` |
| --- | --- | --- |
| pytest | **230 passed, 50 subtests passed** in 10.48 s | 228 passed, 50 subtests passed |
| unittest discovery | **Ran 221 tests — OK** in 8.989 s | Ran 219 tests — OK |
| `node --test` (frontend) | **52 pass, 0 fail** in 290 ms | 52 pass, 0 fail |

The baseline column was measured, not inferred, by checking the commit out separately:

```bash
git worktree add --detach <scratch>/base-wt d9f6958
cd <scratch>/base-wt && python -m pytest backend/tests/ -q
cd <scratch>/base-wt && python -m unittest discover -s backend/tests -t .
```

There are 20 files matching `backend/tests/test_*.py` (`ls backend/tests/test_*.py | wc -l`).

The two Python counts differ because pytest counts parametrised subtests separately;
both runners are required, because the project has been broken under one while green
under the other.

**Frontend testing is pure-function only.** `frontend/package.json` carries no jest,
vitest, testing-library or jsdom, and none was added. The 52 `node --test` cases cover
`helpRouting.js`, `helpSearch.js`, `checklistState.js`, `commonProblems.js`,
`blockDescriptors.js`, `resolveLocale.js` and `settingsGroupGuides.js`. React component
behaviour has **no automated coverage** — see [Not implemented](#not-implemented).

## HTTP surface — repository

```bash
VENDING_WASHER_DATABASE_URL="sqlite:///<scratch copy>.db" python -c \
  "from backend.flask_server import app; [print(sorted(m for m in r.methods if m not in ('HEAD','OPTIONS')), r.rule) for r in sorted(app.url_map.iter_rules(), key=lambda r: str(r.rule))]"
```

**44 non-static rules** (45 including Flask's `static`), in four namespaces:

| Namespace | Rules | Auth |
| --- | --- | --- |
| `/api/*` (kiosk) | 5 | `X-API-KEY` header |
| `/api/dev_admin/*` | 19 | HTTP Basic (`admin_username` / `admin_password_hash`) **and** `dev_admin_enabled=true` |
| `/admin/*` | 19 | HTTP Basic (same credentials) |
| `/generate_code` | 1 | `X-API-KEY` (`@require_api_key`, `flask_server.py:164`) |

Kiosk namespace: `GET /api/ui_state`, `POST /api/scan_code`, `POST /api/start_machine`,
`POST /api/touch_select_machine`, `GET,POST /api/i4_event`.

Dev-admin namespace (19): `unlock`, `status`, `settings` (GET/PATCH),
`generate_api_key`, `machines` (GET/PATCH), `machines/<machine_name>` (PATCH),
`machine-layout` (PATCH), `export-config`, `telemetry`, `diagnostics`, `kiosk_state`,
`remote_scan`, `remote_touch_select`, `remote_reset`, `help/status`, `help/manifest`,
`support_report`.

The `/api/dev_admin/*` namespace uses **Basic auth, not the API key** — verified at
`backend/controllers/dev_admin_api.py:77` (`_valid_admin_auth`). Documents that describe
the panel password as the kiosk API key are stale; the API key is required only as
`current_api_key` when rotating a secret.

Full per-endpoint reference: [`reference/api-reference.md`](./reference/api-reference.md).

## Database — this machine

```bash
sqlite3 "file:codes.db?mode=ro" "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
sqlite3 "file:codes.db?mode=ro" "SELECT 'settings', COUNT(*) FROM settings UNION ALL ..."
```

SQLite file `codes.db` at the repository root. **Ten tables:**

| Table | Rows |
| --- | --- |
| `codes` | 0 |
| `devices` | 6 |
| `machine_configs` | 4 |
| `machines` | 4 |
| `reisa_audit_logs` | 297 |
| `reisa_retry_jobs` | 114 |
| `scan_logs` | 0 |
| `settings` | 34 |
| `settings_audit_logs` | 0 |
| `usage_sessions` | 156 |

`settings_audit_logs` exists but is empty: the configuration audit trail has recorded
nothing yet on this install. `codes` is empty because this machine has been running the
Reisa path historically; `reisa_retry_jobs` holding 114 rows is worth a maintainer's
look before beta.

Table and lifecycle reference:
[`reference/database-schema-and-lifecycle.md`](./reference/database-schema-and-lifecycle.md).

## Machines — this machine

```bash
sqlite3 -header -column "file:codes.db?mode=ro" "SELECT * FROM machines ORDER BY id;"
```

**The internal key and the display name are different strings.** The internal key
(`machines.name`) is what every API call, log line and mapping uses; the display name
(`machines.ui_name`) is only what a customer sees, and it is editable in the panel. Do
not use one where the other is meant.

| id | internal key (`name`) | display name (`ui_name`) | UNI device id | relay ch | i4 device | i4 button | enabled |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `washer1` | Washer 1 | 3 | 0 | 2 | 0 | yes |
| 2 | `dryer1` | Dryer 1 | 4 | 0 | 2 | 1 | yes |
| 3 | `washer2` | Washer 2 | 5 | 0 | 2 | 2 | yes |
| 4 | `dryer2` | Dryer 2 | 6 | 0 | 2 | 3 | yes |

Six devices (`SELECT * FROM devices`): one `button_box` (`shelly-1`), one `i4`
(`shelly-plus-i4`, four inputs, all four machines' buttons), and four `shelly-uni`
telemetry devices — ids 3 and 4 with `metric_source` **`voltage`**, ids 5 and 6 with
`metric_source` **`power`**. The two metric sources are not interchangeable, and the
thresholds below are shared across all four machines regardless:

```bash
sqlite3 -header -column "file:codes.db?mode=ro" "SELECT * FROM machine_configs;"
```

All four machines: `on_threshold` 8, `off_threshold` 3, `on_confirm_ms` 1200,
`off_confirm_ms` 3000, `poll_interval_ms` 1000. Two of them measure volts and two
measure watts against those same numbers — verify that before beta.

## Scanner — this machine

```bash
sqlite3 "file:codes.db?mode=ro" "SELECT key,value FROM settings WHERE key LIKE 'serial%' OR key='scan_timeout';"
```

`serial_port` = `/dev/ttyACM0`, `serial_baudrate` = `9600`, `scan_timeout` = `3`.

These are read **once**, when `_ensure_serial_ready()` first opens the port at startup
(`backend/controllers/qr_scanner.py:232`), and then cached for the life of the process.
They are not read at import, and they are not re-read on change — so a scanner setting
change needs a backend restart.

## Risk-gating settings — this machine

```bash
sqlite3 "file:codes.db?mode=ro" "SELECT key,value FROM settings WHERE key IN (...) ORDER BY key;"
```

| Setting | Value | Meaning at this value |
| --- | --- | --- |
| `backend_relay_enabled` | **`false`** | Relay commands are skipped. Bench/dry-run mode; no physical machine will start. |
| `dev_admin_enabled` | **`true`** | `/dev/admin` and `/api/dev_admin/*` are reachable behind Basic auth. |
| `telemetry_enabled` | **`true`** | Telemetry polling runs; availability is real. |
| `provider_default` | **`local`** | Validation goes to the `codes` table, not Reisa. |
| `provider_reisa_enabled` | **`false`** | Reisa path off. |
| `button_box_enabled` | **`true`** | Physical button-box input accepted alongside touch. |

Also observed: `machine_reservation_minutes` = 10, `kiosk_poll_interval_ms` = 1000,
`code_expiration_days` = 0, `log_level` = `INFO`, `kiosk_input_mode` =
`hardware_buttons` (legacy metadata; see the drift note in
[`ai/system-quick-map.md`](./ai/system-quick-map.md)).

> [!WARNING]
> This is **not** the configuration the kiosk is intended to run in production.
> `provider_default=local` with an empty `codes` table, `provider_reisa_enabled=false`
> and `backend_relay_enabled=false` means no customer flow can complete on this
> machine right now. Confirm the intended runtime configuration with the maintainer
> before beta; do not change these settings as a side effect of another task.

The whitelist that governs what the panel may write is `SETTING_SCHEMA` in
`backend/services/dev_admin_service.py`: **34 keys in 11 groups, 29 editable**, exactly
matching the 34 rows in the `settings` table. Five are restart-required
(`cors_allowed_origins`, `log_level`, `scan_timeout`, `serial_baudrate`, `serial_port`)
and fourteen are marked high risk. Per-key detail:
[`reference/settings-catalog.md`](./reference/settings-catalog.md).

## Help Hub corpus — repository

```bash
python -m backend.help.cli --check    # exit 0
python -c "import json; from backend.help import cli; m=json.loads(cli.ADMIN_ARTIFACT.read_text('utf-8')); ..."
```

| Fact | Value |
| --- | --- |
| Admin guides (`docs/admin-guides/`) | **15**, `trust_class: admin`, schema version 1 |
| Public guides (`docs/public-help/`) | **3** — `backend-unavailable`, `kiosk-screen-blank`, `network-unavailable` |
| Default locale | `is` (Icelandic), fallback `en` |
| Icelandic full translations shipped | **0** |
| Icelandic discovery stubs shipped | **9** |
| Icelandic translations withheld | **6** |

Admin guides by category: `machines_telemetry` 6, `daily_operation` 2, `codes_reisa` 2,
`hardware_network` 2, `admin_recovery` 1, `kiosk_display` 1, `scanner` 1.

The six ranked "Common problems", in order: `machine-unavailable`,
`machine-does-not-start`, `all-machines-available-telemetry-stale`, `code-rejected`,
`scanner-not-scanning`, `kiosk-cannot-reach-backend`.

Those same six are the six withheld Icelandic translations. Their Icelandic text is
written and sits at `translation_status: review`, awaiting the maintainer's language
review; the compiler therefore withholds it and the operator sees English. This is the
**intended** state, recorded in `manifest["excluded_translations"]` and asserted by
tests. Do not flip a `translation_status` to `published` to close it.

The nine guides that ship an Icelandic **stub** (discoverable by Icelandic search, body
rendered in English): `admin-access-recovery`, `admin-panel-orientation`,
`machine-technical-mapping`, `no-telemetry-reading`, `reisa-configuration`,
`settings-requiring-restart`, `tune-thresholds`, `using-diagnostics`,
`wrong-machine-starts`.

Authoring rules: [`admin-guides/README.md`](./admin-guides/README.md) — added by the
Task 18 documentation work, so it exists at HEAD but not at the `d9f6958` baseline.

## How the system is started — this machine

`python -m backend.app` is the only entry point that starts the full runtime. Reading
`backend/app.py`, it runs `init_db`, `bootstrap_settings`,
`bootstrap_devices_and_machines` and `ensure_backend_relay_setting_exists`, then starts
daemon threads for the code-cleanup scheduler, the Reisa retry worker, the telemetry
poll and the scanner listener, and runs Flask on `0.0.0.0:5000` with `debug=True` and
`use_reloader=False` (`backend/app.py:29`).

`python -m backend.flask_server` starts HTTP routes only — no background workers and no
`bootstrap_settings`, which leaves `api_key` unset on a fresh database.

Two convenience scripts exist at the repository root: `run-backend.sh` (activates
`.venv`, then `python -m backend.app`) and `run-frontend.sh` (sets `DISPLAY=:0` and a
hardcoded `XAUTHORITY=/home/hamrar/.Xauthority`, then `npm run dev`). The frontend runs
as a **Vite dev server on port 3000** proxying `/api` to `http://localhost:5000`; there
is no production build being served.

Full sequence: [`architecture/runtime-lifecycle.md`](./architecture/runtime-lifecycle.md).

## Not implemented {#not-implemented}

Verified absent at HEAD on this branch, not merely undocumented:

- **No systemd unit.** `find . -name "*.service"` (excluding `node_modules`) returns
  nothing. The backend is started by hand or by `run-backend.sh` and dies with its
  terminal.
- **No install script.** The only shell scripts at the root are `run-backend.sh` and
  `run-frontend.sh`, neither of which installs anything. Setup is the manual sequence in
  [`operations/runbooks/install-and-bootstrap.md`](./operations/runbooks/install-and-bootstrap.md).
- **No autostart.** Nothing in the repository registers a service, a cron entry, an
  `@reboot` hook, or a desktop autostart file. After a power cut the kiosk does not come
  back on its own.
- **No restart from the panel.** `/dev/admin` shows the restart command and refuses to
  run it. There is no `restart_backend` action behind the manifest's `actions` field —
  it is a label, not a button — precisely because there is no supervised service to
  restart safely. This is the largest remaining self-service gap: an operator who needs
  a restart still needs a person with shell access.
- **No frontend component tests.** No jest, vitest, testing-library or jsdom in
  `frontend/package.json`. Three behaviours are therefore hand-verified only:
  contextual Help opening from Settings with unsaved edits, the same from the machine
  technical-mapping drawer, and `#help/<unknown-id>` rendering the not-found state.
- **No production frontend serving.** Vite dev server only; `npx vite build` succeeds
  but nothing serves the output.
- **No config import/restore in the panel.** Export exists; restore is deliberately a
  manual SQLite restore.
- **No per-user audit attribution.** `settings_audit_logs` records what changed, never
  who — there is one shared admin account.
- **No account lockout or rate limiting** on repeated failed admin logins.
- **No AI assistant, embeddings, feedback storage, or decision-tree engine** in the Help
  Hub. All were explicitly excluded from its scope.

## Known code-level discrepancies

Found by reading source during Task 17/18 verification, left unfixed because they are
code changes outside a documentation task. Recorded so they are not rediscovered as
novel:

1. *(Fixed 2026-09-04.)* Three operator-visible strings asserted that the dev/admin panel
   is unlocked with an API key. It is not: `require_dev_admin`
   (`backend/controllers/dev_admin_api.py`) checks the `dev_admin_enabled` kill switch and
   then HTTP Basic auth against `admin_username` / `admin_password_hash`, and no API key is
   involved. The frontend variable holding the base64 credentials is merely *named*
   `apiKey`, which is where the wording came from. Corrected in
   `dev_admin_service.py:77` (the `api_key` schema description, rendered in Settings),
   `DevAdminShell.jsx:49` (the panel's own banner) and `DevAdminPage.jsx:88` (the 401
   message).
2. `METRIC_SOURCES` in `dev_admin_service.py` offers `pulse`, but
   `telemetry.py:_read_metric` has no branch for it, so every read returns `None` and the
   machine is marked offline. Conversely `_read_metric` handles `adc`, which the drawer
   does not offer.
3. `DiagnosticsPanel.jsx` renders histogram rows from `count/avg/p50/p95/max`, while
   `metrics.py` emits `count/avg_ms/p95_ms/p99_ms/max_ms`, so only `count` ever appears.
4. Nothing validates that a machine's OFF threshold is below its ON threshold.
