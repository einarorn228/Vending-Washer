# Admin Help Hub — Design Spec

Status: approved in direction, pending spec review
Date: 2026-09-02
Branch context: `UI-changes`

## 1. Purpose

Give a site administrator a first-class support system inside `/dev/admin` so that most
normal kiosk problems are resolved without a developer connecting over SSH/VPN.

The system has **two legitimate outcomes**, and both are success:

1. **Self-service resolution** — the operator follows a guide and fixes the problem entirely
   from `/dev/admin`.
2. **High-quality escalation** — the problem genuinely needs SSH, process recovery, a code
   fix, or physical intervention, and the operator hands the developer precise evidence
   instead of "the machine isn't working".

Escalation is not a failed Help experience. The journey is
`problem → guide → safe diagnosis → evidence collected → clear escalation report`,
never `problem → guide → "contact developer"`.

### Why this scope

An audit of the 18 rows in `docs/operations/runbooks/troubleshooting-matrix.md` classified
each remedy by whether an administrator could execute it from a browser:

- ~5 are fully resolvable in `/dev/admin` today.
- ~6 are blocked on exactly one missing capability: a backend restart.
- ~6 genuinely require SSH, physical access, or a code fix.

Documentation alone therefore converts roughly a quarter of support cases. The escalation
report is what makes the remaining cases cheaper. A supervised restart action would convert
the middle group, but no systemd unit exists yet and first physical beta is imminent, so it
is deliberately deferred (§12).

## 2. Non-goals

Explicitly out of scope for this build:

- AI assistant, embeddings, vector database, any LLM integration.
- Any hardware-affecting or process-control action, including `restart_backend`.
- Decision-tree / workflow / branching engine.
- Feedback table (thumbs up/down), analytics storage, user accounts or permissions.
- Translating the rest of the `/dev/admin` UI.
- A general documentation website or CMS.
- Any endpoint that reads arbitrary filesystem paths or exposes `docs/` wholesale.
- Redesigning existing `/dev/admin` tabs or changing kiosk behaviour.

## 3. Audience and language

The primary reader is an **Icelandic-speaking site operator**, not a developer.

- Icelandic (`is`) is the default Help language; English (`en`) is the fallback.
- Bilingual architecture from day one; a guide may exist in one language only, and the
  system knows that explicitly rather than pretending otherwise.
- Locale resolution order: user selection → deployment default (`is`) → `en`.
- When a fallback occurs the UI states it plainly, e.g.
  *"Þessi leiðbeining er ekki enn til á íslensku — sýni enska útgáfu."*
  Languages are never silently mixed.
- A Help-local language selector is acceptable; Help locale is **not** hardwired to the
  admin UI language, so the same infrastructure can later carry full admin localisation.

**Technical identifiers are never translated**: setting keys, machine IDs, API field names,
error codes, IP addresses, Reisa action identifiers, commands, filenames. Human-facing text
around them is localised. This matters because an operator may forward a support report to a
developer. The inline `setting_ref` block type (§6.3) makes this structural rather than a
convention authors must remember.

## 4. Content architecture

### 4.1 Two physically separate trust tiers

```
docs/admin-guides/is/<category>/<guide-id>.md     trust class: admin
docs/admin-guides/en/<category>/<guide-id>.md     trust class: admin
docs/public-help/<guide-id>.md                    trust class: public_bootstrap
```

**Separate directories, not a `visibility:` frontmatter flag.** Publishing content to the
public tier requires moving a file *and* updating a snapshot test that enumerates every
public guide ID. Accidental exposure must require an obvious source diff, never a typo.

`admin` content is served only over authenticated endpoints. `public_bootstrap` content is
compiled into the frontend build and is readable by anyone on the kiosk LAN — that is its
definition, and it constrains what may go in it (§10.2).

**Static frontend assets are never a privacy boundary.** Verified on the current production
build: there is one JS chunk with no code splitting, and it already contains `DISABLE DEV
ADMIN`, `Danger zone`, `backend_relay_enabled` and the 34 `settingHelp.js` explanations.
Anyone on the LAN can fetch `http://<pi>:3000/assets/index-*.js`. Code splitting is
worthwhile hygiene but is **not** access control.

### 4.2 Existing runbooks are source material, not the corpus

`docs/` stays developer documentation. Help guides are *operator documentation derived from
developer documentation*: extract verified facts, symptoms, validated procedures, safety
constraints and real field incidents; rewrite for the operator. Never publish a developer
document because it happens to exist.

### 4.3 Categories and kinds — two orthogonal axes

`category` (subsystem), aligned deliberately with the backend `SETTING_GROUPS` spine so that
`related_settings` navigation and contextual-help placement fall out without a second
mapping table:

`daily_operation` · `machines_telemetry` · `codes_reisa` · `scanner` ·
`hardware_network` · `admin_recovery` · `kiosk_display`

`kind` (shape): `troubleshooting` | `procedure` | `concept` | `recovery`

`troubleshooting` and `settings` are deliberately **not** categories — the first would
swallow most of the corpus, the second overlaps everything. `beta_testing` is deliberately
absent: temporal labels become stale information architecture.

Category sizes will be uneven — at launch `machines_telemetry` holds 6 of 15 guides,
because telemetry genuinely is the dominant failure surface. That imbalance is a reason the
landing page leads with **Common Problems** rather than category browse; categories are a
secondary axis for orientation, not the primary way an operator in trouble finds a guide.

**Common Problems is derived, never hand-maintained**: the landing rail lists
`kind: troubleshooting` guides ordered by optional `common_problem_rank`. The shortcut list
cannot drift from the corpus because it *is* the corpus.

### 4.4 Metadata schema

Deliberately small. Every field costs authoring time on all 50–200 future guides.

**Required in every file** (localised where noted):

| Field | Neutral/localised | Notes |
|---|---|---|
| `id` | neutral | stable, kebab-case, shared across locales |
| `locale` | neutral | `is` or `en` |
| `title` | localised | |
| `summary` | localised | one or two sentences; shown in search results |

**Canonical-only, inherited by translations** — declared on the locale marked
`canonical: true` (exactly one per guide ID):

| Field | Notes |
|---|---|
| `category` | from §4.3 vocabulary |
| `kind` | from §4.3 vocabulary |
| `risk` | `low` / `medium` / `high` |
| `status` | `draft` / `review` / `published` |
| `last_reviewed` | ISO date |
| `related_guides` | list of guide IDs |
| `related_settings` | list of setting keys, validated against `SETTING_SCHEMA` |
| `diagnostics` | list of server-defined diagnostic group names (§8) |
| `actions` | optional list of named action IDs, e.g. `restart_backend` |
| `common_problem_rank` | optional integer |

**Localised, optional:**

| Field | Notes |
|---|---|
| `search_aliases` | semantic synonyms only (§7.3) |
| `stub` | `true` when the file carries metadata but no body (§4.6) |

**Inheritance rule.** A translation may omit any canonical-only field and inherit it. If it
declares one, the validator requires exact equality with the canonical value and fails the
build otherwise. Authors write the minimum; drift becomes a build error rather than a latent
inconsistency. No third sidecar metadata file.

### 4.5 Stable section anchors

Auto-slugged headings cannot align across locales (`check-telemetry` vs
`athugadu-fjarmaelingar`), and positional alignment breaks silently the first time one
translation gains a heading. So citeable H2 headings carry an explicit language-neutral
anchor:

```markdown
## Check telemetry {#check-telemetry}
## Athugaðu fjarmælingar {#check-telemetry}
```

H2 is both the citation target and the RAG chunk boundary, so the annotation is paid once
for two purposes. Deeper headings do not require anchors. `machine-unavailable#check-telemetry`
then resolves in both languages, and future AI citations align across a fallback boundary.

### 4.6 Translation stubs

Guide-level fallback fixes *reading* but not *finding*: an Icelandic query cannot match an
English-only body, so the operator never reaches the fallback banner.

A **stub** is a guide file with localised `title`, `summary` and `search_aliases` but no
body (`stub: true`). It is indexed in Icelandic, found in Icelandic, opens with the fallback
notice, and renders the canonical body. Cost is two short fields instead of two hundred
lines. This is what makes Icelandic-first real at search time on day one rather than after
the whole corpus is translated.

A stub inherits the canonical body **and** the canonical checklist; translating the
checklist is not a precondition for Icelandic discoverability.

### 4.7 Troubleshooting checklists

Optional, for `kind: troubleshooting` and `procedure` guides. Prose remains the primary
format. This is guided inspection and evidence collection — **not** executable logic.

```yaml
checks:
  - id: telemetry-enabled          # neutral, stable, shared across locales
    question: "Er fjarmæling virk?"          # localised
    look_for: "Diagnostics → Live readings"  # localised
    expected: "Fjarmæling á að vera virk."   # localised
    route: diagnostics                       # neutral, admin route id
    diagnostics: [settings.telemetry]        # neutral, server-defined groups
    problem_guide: telemetry-disabled        # neutral, guide id, optional
```

The operator marks each check `ok` | `problem` | `unsure` | `not_checked`. When a check is
marked `problem`, the UI statically surfaces `problem_guide` if declared. That is the whole
mechanism.

**Explicitly excluded:** `if_true`/`if_false` routing, conditions, expression evaluation,
nested branches, automatic navigation, node graphs, automatic diagnosis. These turn the
checklist into a second content language that must be authored, translated, tested and kept
aligned with the prose. If beta shows four or five problems genuinely need branching, that is
designed separately from evidence, not grown into accidentally.

`unsure` and `not_checked` are first-class results, not absences — they are diagnostic signal
a branching engine would have swallowed.

Check IDs are shared across locales; the validator rejects a translation that changes the
check structure.

## 5. Compiler and validator

**One compiler implementation, two configured invocations, two artifacts.** The security
boundary comes from separate source roots, explicit invocation, separate outputs, separate
serving rules and snapshot tests — never from duplicated parsing logic, which would let the
two trust tiers drift apart.

```python
compile_help(root=ADMIN_ROOT,  trust_class="admin")            -> admin-help-manifest.json
compile_help(root=PUBLIC_ROOT, trust_class="public_bootstrap") -> public-help-manifest.json
```

Written in **Python**, so the validator, anchor-parity checks, duplicate-ID detection and
link resolution run inside the existing `pytest` suite rather than a second toolchain.

### 5.1 Markdown parsing — decision deferred to the implementation plan

The security property is **not** "zero dependencies"; it is that raw Markdown/HTML is never
rendered in the admin browser and the compiler emits only allowlisted block types.

The plan will compare head-to-head, on tables, nested lists, fenced code, links, escaping,
Icelandic Unicode, `{#anchor}` syntax and malformed author input:

- **Option 1** — a deliberately restricted custom parser for the small syntax we officially
  support.
- **Option 2** — a small mature compile-time Markdown library, with our compiler converting
  its output into our strict block schema.

Neither is pre-selected. Raw HTML in guide source is a compile error either way.

### 5.2 Validation rules (build fails on any violation)

- Unknown or missing required metadata field; unknown `category`, `kind`, `risk`, `status`.
- Duplicate guide ID within a locale; duplicate anchor within a guide.
- Exactly one `canonical: true` locale per guide ID.
- Translation overriding an inherited neutral field with a different value.
- Anchor-set parity between full (non-stub) translations of the same guide.
- Unresolvable `related_guides`, `problem_guide`, or internal `guide_link` targets.
- `related_settings` key not present in the backend `SETTING_SCHEMA`.
- `diagnostics` group not in the server-side allowlist (§8).
- `actions` ID not in the known-action registry.
- Raw HTML in source.
- Check ID drift between locales of the same guide.
- Public-tier snapshot mismatch (§10.2).
- Non-determinism: recompiling must byte-match the committed artifact.

### 5.3 Artifact handling

Manifests are **committed generated artifacts**, and a test recompiles and asserts
byte-equality with the committed file. This gives deterministic, diffable, reviewable
output; guarantees guides and code ship and roll back together; and removes any build step
from deployment.

`generated_at` is deliberately omitted — it would defeat diffability. Provenance comes from
`build_id` (git revision when cleanly available, otherwise `null`).

## 6. Manifest schema

```jsonc
{
  "schema_version": 1,
  "trust_class": "admin",
  "build_id": "087efbb",
  "default_locale": "is",
  "locales": ["is", "en"],
  "guide_count": 15,
  "categories": [ { "id": "machines_telemetry", "titles": { "is": "...", "en": "..." } } ],
  "guides": {
    "machine-unavailable": {
      "id": "machine-unavailable",
      "canonical_locale": "en",
      "category": "machines_telemetry",
      "kind": "troubleshooting",
      "risk": "medium",
      "status": "published",
      "last_reviewed": "2026-09-02",
      "related_guides": ["tune-thresholds"],
      "related_settings": ["telemetry_enabled"],
      "diagnostics": ["machine.telemetry", "machine.thresholds"],
      "actions": [],
      "common_problem_rank": 1,
      "locales": {
        "en": {
          "title": "...", "summary": "...", "search_aliases": ["..."],
          "stub": false,
          "sections": [ { "anchor": "check-telemetry", "heading": "Check telemetry",
                          "blocks": [ /* §6.3 */ ] } ],
          "checks": [ /* §4.7 */ ]
        },
        "is": { "title": "...", "summary": "...", "search_aliases": ["..."], "stub": true }
      }
    }
  },
  "search": { /* §7 */ }
}
```

### 6.3 Allowlisted render blocks

Block: `paragraph`, `heading`, `ordered_list`, `unordered_list`, `code_block`, `table`,
`callout` (`note` | `warning` | `danger`), `guide_link`, `external_link`.

Inline: `text`, `strong`, `em`, `code`, `setting_ref`, `guide_link`, `external_link`.

`setting_ref` carries a validated setting key and renders distinctly; it is structurally
never translated, satisfying §3.

The frontend renders these as React elements. **No `dangerouslySetInnerHTML` anywhere.**

## 7. Search

Runs in the admin browser after the authenticated fetch: instant, offline, no round trips,
no server load on the Pi.

### 7.1 Normalisation

Lowercase → Icelandic folding (`þ→th`, `ð→d`, `æ→ae`, `ö→o`, and accent stripping via NFD)
→ token split. Folding is for **matching only**; display always uses the original text.

### 7.2 Fold + prefix matching

Alias-only search fails on Icelandic morphology: `þvottavélin virkar ekki` does not
exact-match the alias `þvottavél`, and enumerating inflected forms is exactly the authoring
tax to avoid. Because Icelandic inflection is **suffixal**, the stem is stable at the front,
so: *the shorter of (query token, indexed term) is a prefix of the longer*.

Validated against realistic operator input — 10/10 matched, covering definite forms
(`þvottavélin`), plurals/genitives (`þvottavélar`, `stillingar`), ASCII transliteration
(`thvottavel`), and a head-initial compound (`þvottavélarbilun`).

**Noise guards:**
- Minimum normalised token length of 4 for any prefix match.
- Exact matches always outrank prefix matches in the same field.
- Prefix score scaled by `len(shorter) / len(longer)`, penalising distant partial overlaps.
- A short function-word stoplist (both languages) excluded from prefix matching.

### 7.3 Field weighting

Descending: `title` → `search_aliases` → `summary` → H2 `heading` → `body`. Aliases carry
**semantic synonyms only** (`washer ↔ þvottavél`, `dryer ↔ þurrkari`, `relay ↔ rofi`,
`unavailable ↔ upptekin / ekki laus`) — never grammatical endings, which prefix matching
already handles. No stemmer, no NLP dependency.

Search covers the requested locale plus stubs, so untranslated guides remain discoverable in
Icelandic.

## 8. Support projection — one shared mechanism

The escalation report and future system-aware guide cards need the same thing: a versioned,
allowlisted, read-only projection of runtime state. It is built **once**.

A backend `support` service owns: what each diagnostic group means, which fields are safe,
redaction, and runtime gathering. **Guides only name groups.** Guide content never reads
DB or runtime data.

### 8.1 Groups are server-controlled

The client must never name backend data groups. It cannot invent field paths.

Request carries only: optional `guide_id`, optional `machine_id`, optional checklist results,
and `locale`. The backend then:

1. Looks up the guide by stable ID in the authenticated compiled manifest.
2. Reads that guide's approved `diagnostics` declarations.
3. Maps them through the server-side group allowlist.
4. Gathers, redacts, and returns the structured report.

With no `guide_id`, a fixed server-defined core group set is used. A query parameter such as
`?groups=...` is explicitly not part of the API.

### 8.2 Contents

Core (always): timestamp, `schema_version`, `build_id`, kiosk/UI runtime state, provider
mode, telemetry enabled, relay-control enabled, scanner status, Reisa configured/not
(never the token), `guide_id`, `locale_requested`, `locale_shown`, checklist results
(`check_id` + result).

Group-scoped: machine ID and display name, enabled/available state, metric source, current
live value, ON/OFF thresholds, above/below durations, safe device mapping metadata, last
safe error/status, non-secret setting values.

**Never**: API keys, bearer tokens, password hashes, raw credentials, QR/payment/order
payloads, arbitrary log or file contents, anything outside the allowlist.

### 8.3 Shape

Canonical structured data uses stable internal English identifiers regardless of locale;
only the human-readable copied rendering is localised. This gives readable Icelandic reports
for operators and stable parseable data for developers and future AI.

`locale_requested` vs `locale_shown` also yields, for free, a usage-ranked translation
backlog: which guides Icelandic operators most often read in English.

## 9. Backend API

All admin endpoints sit behind the existing `require_dev_admin` decorator (403 when the kill
switch is off, 401 on bad credentials).

| Endpoint | Purpose |
|---|---|
| `GET /api/dev_admin/help/manifest` | full compiled admin manifest (all locales) |
| `GET /api/dev_admin/help/status` | `schema_version`, `build_id`, `guide_count`, health |
| `POST /api/dev_admin/support_report` | structured + rendered support report (§8) |

At the expected corpus size one manifest is simpler and comfortably within budget; the plan
will size it and split into `index` + `guides/<id>` only if measurement says so.

**Lookup is `manifest.guides[guide_id]`.** No endpoint accepts a filesystem path, filename,
`../`, or any arbitrary `docs/` read. An unknown ID is a 404 from a dict miss — the arbitrary
file reader risk is structurally impossible, not merely guarded.

### 9.1 Manifest loading must never break the backend

**Help can fail. The kiosk and backend cannot fail because Help failed.**

The manifest is loaded and cached once, behind a failure-isolated boundary:

- Attempt load and schema-version validation.
- On success, cache the parsed manifest.
- On failure (missing, malformed, unreadable, incompatible `schema_version`), store a
  structured *unavailable* state and log the reason clearly.
- Help endpoints then return a well-formed "help unavailable" response with the reason.
- Everything else continues normally.

No import-time exception may escape. Errors are logged understandably, never silently
swallowed. This is a backend guarantee independent of the frontend error boundary.

Required test: with a corrupt or missing manifest — `python -m backend.app` still starts,
kiosk APIs still work, `/dev/admin` non-Help tabs still work, Help reports unavailable.

## 10. Security boundaries

### 10.1 Summary

- Admin guide content is served only after authentication; never bundled into frontend assets.
- No arbitrary file/path API; guide IDs are validated dict keys from a compiled manifest.
- No raw HTML rendering; strict allowlisted block schema.
- Diagnostic groups are server-controlled and allowlisted; the client cannot name fields.
- Secrets are never included in guides, manifests or reports — presence booleans only.
- Public tier is separately rooted, separately compiled, and snapshot-tested.

### 10.2 Public bootstrap tier

Three guides, deliberately tiny, safe for any person on the kiosk LAN to read: *backend
unavailable*, *kiosk screen blank*, *network unavailable*. Content is limited to
non-privileged physical checks, safe retry/refresh guidance, and escalation language.

It contains **no privileged recovery path**: no admin unlock/re-enable commands, no
credential or API-key procedures, no hardware mapping detail, no relay enablement, no
privileged commands.

A snapshot test enumerates every public guide ID; adding one requires updating that test.

### 10.3 Accepted trade-off — lockout

Because Help sits behind `require_dev_admin`, the authenticated *Admin access & recovery*
guide is unreachable during a genuine lockout. That guide serves an authenticated admin
preparing for or diagnosing access configuration. During a true lockout the public tier says
only *"Administrator access is unavailable. Contact the system maintainer."* The privileged
recovery path stays developer-level. **This is intentional and accepted.**

## 11. Frontend

### 11.1 Two presentations, one renderer

- **Help tab** — browse, search, categories, Common Problems rail, full guide reading.
- **Contextual drawer** — an overlay above the current tab, following the existing
  `MachineDetailDrawer` pattern.

Both render the same guide from the same block renderer.

**Contextual help never navigates.** The drawer preserves unsaved Settings drafts, Machine
Card edits and advanced mapping changes, which is the entire reason it is a drawer.

### 11.2 Routing — includes a verified defect fix

`readTabFromHash()` is currently `TAB_IDS.includes(hash) ? hash : 'overview'`. A deep link
such as `#help/machine-unavailable` fails that check and **silently opens Overview**. This is
a real defect that every contextual link and future AI citation would hit.

The hash parser is extended so these are first-class routes:

- `#help` — Help landing
- `#help/<guide-id>`
- `#help/<guide-id>/<section-anchor>`

Existing tab hashes keep working. An unknown guide ID or anchor produces a clear Help
**not-found** state, never a silent fallback to Overview.

### 11.3 Contextual help placements

Six, deliberately. Per-setting `?` icons already exist via `settingHelp.js`; Help attaches
one level up to avoid clutter.

1. `MachineDetailDrawer` — technical mapping (highest-consequence action in the panel).
2. `DiagnosticsPanel` — live readings and threshold tuning.
3. Settings **group** headers (11 links, not 34).
4. `SecuritySettingsPanel` — Reisa configuration.
5. `DangerZonePanel` — replaces inline recovery prose with a link to the maintained guide.
6. Restart-required banner — the most common "why can't I finish this?" moment, and the
   future home of the `restart_backend` action.

### 11.4 Failure and offline behaviour

| Condition | Behaviour |
|---|---|
| Authenticated, manifest healthy | Full Help Hub |
| Dev admin disabled | Help unavailable with the rest of the panel, as designed |
| Backend unreachable | Only the public bootstrap tier |
| Manifest malformed/missing | "Help content unavailable"; other tabs unaffected |
| Requested locale missing | Fallback notice + canonical body (§3, §4.6) |
| Search index failure | Category and guide navigation still work |

Help mounts inside its own error boundary and fails independently of the admin shell.

## 12. Future capability path — designed for, not built

- **Named actions.** Guides reference action IDs (`restart_backend`); the UI renders whatever
  it can currently perform and otherwise shows the documented manual path. Guide prose does
  not hardcode shell commands. When a supervised systemd service exists, a narrowly
  allowlisted, audited, confirmation-gated restart action drops in without rewriting content.
- **System-aware cards.** A second rendering of the §8 projection. No new data path.
- **AI retrieval.** The §4.5 section chunks are the retrieval unit; citations are
  `guide-id#anchor` with locale stated. Retrieval searches the selected locale first, may
  fall back to the canonical guide, and must surface that fallback rather than inventing a
  translation. First AI version is read-only: explain, diagnose, cite, point — never change
  settings, enable relays, start machines, alter mappings or rotate credentials.

### 12.1 Measurement, without building analytics

No analytics storage now. Identifiers are designed so these stay answerable later: which
guides most often precede a support report; which checks most often become `problem` or
`unsure`; which guides Icelandic users most often see in English; which common problems open
most; which guides are never used.

### 12.2 Setting-description consolidation

Two description sources already exist: `SETTING_SCHEMA.description` (backend) and
`settingHelp.js` (frontend). **The Hub must not become a third** — guides reference settings
by key and never restate what a setting *is*.

Recommended evolution, as its own small change after beta: move `settingHelp.js` text into
the backend schema as a `help` field beside `description`, serve it with the settings
payload, and delete `settingHelp.js`. Two sources collapse to one; the Hub stays the third
thing it should be — procedures and diagnosis, not definitions.

## 13. First-beta scope

**15 admin guides + 3 public bootstrap guides.**

### Tier 1 — human-reviewed Icelandic (6)

| # | Guide | Category | Kind |
|---|---|---|---|
| 1 | Machine shows unavailable even though it is idle | machines_telemetry | troubleshooting |
| 2 | Machine does not start after selection | machines_telemetry | troubleshooting |
| 3 | All machines show available / telemetry stopped or stale | machines_telemetry | troubleshooting |
| 4 | QR / Reisa code rejected or scan does not advance | codes_reisa | troubleshooting |
| 5 | Scanner is not scanning | scanner | troubleshooting |
| 6 | Kiosk shows a stale screen or cannot reach the backend | kiosk_display | troubleshooting |

Guide 3 is promoted on evidence: it is the only guide backed by a **recorded field incident**
(`telemetry_enabled=false` plus a stale backend process made every machine report available),
and it is commercially the worse failure — the customer pays and selects a machine that is
actually running. Its operator-checkable signal already exists in Diagnostics
(`seconds_since_read` climbing, `last_value` frozen). Guide 6 is likewise incident-backed
(Chromium `GET` caching, the API-key/`.env` race after a Vite restart); its safe subset also
appears in the public tier, with the authenticated diagnostic version here.

Guides 1 and 3 are adjacent but distinct entry symptoms — "this machine looks busy and isn't"
versus "everything looks free and isn't" — and cross-link. The spec notes this so authors do
not write duplicates.

### Tier 2 — English canonical + Icelandic discovery stubs (9)

| # | Guide | Category | Kind | Risk |
|---|---|---|---|---|
| 7 | Tuning machine ON/OFF thresholds safely | machines_telemetry | procedure | medium |
| 8 | No telemetry / live reading is missing | machines_telemetry | troubleshooting | medium |
| 9 | Reisa connection and configuration troubleshooting | codes_reisa | troubleshooting | high |
| 10 | Machine technical mapping: Shelly IP, relay channel, I4 | hardware_network | procedure | **high** |
| 11 | Wrong physical machine starts | hardware_network | troubleshooting | **high** |
| 12 | Admin access and dev-admin recovery | admin_recovery | recovery | high |
| 13 | Settings that require a restart | daily_operation | concept | medium |
| 14 | Using Diagnostics | machines_telemetry | concept | low |
| 15 | Admin panel orientation: what you can safely change | daily_operation | concept | low |

Guide 11 is kept on **consequence, not frequency** — there is no incident history, but a
wrong relay mapping starts the wrong physical machine. Guide 10 is the contextual target from
`MachineDetailDrawer`.

Backup/export does **not** get a standalone guide; it becomes a prominent callout inside the
high-risk procedures (10, 11, 12) and a section in guide 15.

### Public bootstrap tier (3)

Backend unavailable · Kiosk screen blank · Network unavailable. Constrained by §10.2.

### Authoring split

I own technical correctness and structure: inspect source, settings, diagnostics and UI;
determine the safest troubleshooting sequence; produce the canonical structure and checklist;
draft English; produce an Icelandic draft explicitly marked as needing language review. The
maintainer owns final Icelandic voice for Tier 1 — terminology, operator register, natural
wording, clarity under stress. Tier 2 ships English canonical plus Icelandic discovery stubs;
full translation follows measured fallback frequency.

Guides are not created to fill categories. One excellent guide beats five weak articles.

## 14. Testing

- Compiler/validator unit tests for every §5.2 rule.
- Determinism: recompile byte-matches the committed manifest.
- Public-tier snapshot: exact list of public guide IDs.
- Secret-leak test: no setting key marked secret, and no known secret value pattern, appears
  in either manifest.
- Backend failure isolation: corrupt/missing manifest → backend starts, kiosk APIs work,
  Help reports unavailable.
- API: auth required; unknown guide ID 404s; no path traversal reachable.
- Support report: allowlist honoured, secrets absent, guide-declared groups respected,
  client-supplied group names ignored.
- Search: fixture queries in both languages, including the Icelandic inflection set.
- Anchor parity and link resolution across locales.
- Frontend: hash routing including `#help/...`, unknown-ID not-found state, drawer preserves
  unsaved drafts.

## 15. Open assumptions

1. **Markdown parser choice** — custom restricted parser vs small mature compile-time
   library. Deliberately deferred to the implementation plan (§5.1).
2. **Manifest delivery shape** — single manifest assumed; split into `index` + per-guide only
   if measured size warrants (§9).
3. **Icelandic category and UI labels** — the English IDs are frozen; the Icelandic display
   strings need maintainer wording.
4. **Thin categories at launch.** Three categories hold exactly one guide each:
   `scanner` (5), `admin_recovery` (12), `kiosk_display` (6). `scanner` and `admin_recovery`
   are genuine subsystems with their own runbooks and will grow, so they stay. `kiosk_display`
   is the marginal one — if it still holds a single admin guide after beta, fold guide 6 into
   `daily_operation` and retire the category.
5. **Committed manifest artifacts** — assumed committed with byte-equality enforcement
   (§5.3). If generated artifacts in git are unwanted, the alternative is a deploy-time
   compile step, which reintroduces version skew.
