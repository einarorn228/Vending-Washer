# Authoring admin help guides

This directory is the **source** of the protected Help Hub shown inside `/dev/admin`.
Nothing here is served directly. Every guide is compiled into a single manifest,
`backend/help/generated/admin-help-manifest.json`, and the backend serves only that
manifest. If a guide does not compile, the build fails and **no** manifest is
written — a defective guide never reaches an operator mid-incident.

The public tier lives in a separate tree, `docs/public-help/`, compiled by the same
compiler into `frontend/src/generated/public-help-manifest.json`. It is bundled into
the frontend and readable by anyone on the LAN. The rules below apply to both trees;
the extra rules for the public tier are in [Two trust classes](#two-trust-classes).

Source of truth for anything this file summarises:
`backend/help/schema.py` (the closed vocabularies), `backend/help/frontmatter.py`
(the frontmatter subset), `backend/help/blocks.py` (the Markdown subset),
`backend/help/compiler.py` (inheritance and translation gating), and
`backend/help/validator.py` (cross-guide rules).

## Layout

```
docs/admin-guides/<locale>/<category>/<guide-id>.md
docs/public-help/<guide-id>.md
```

The compiler walks the tree with `rglob("*.md")` and takes identity from the
frontmatter, not the path. `README.md` **at the tree root** is the one reserved
filename (`compiler.RESERVED_FILENAMES`): it is skipped, so authoring documentation —
this file — can live beside the content without pretending to be a guide. The skip is
root-only on purpose: a `README.md` deeper in the tree sits where guides live, so it
still fails the build rather than vanishing silently. Directory names are therefore a convention for humans
and should match the `category` field; the `<locale>` directory should match the
`locale` field. Locales are `en` and `is`. The **default locale is `is`**
(`schema.LOCALES[0]`) — that is what an operator sees unless they switch.

## Frontmatter

The file must begin with `---`, and the block must be closed with `---`. The parser
is deliberately not YAML. It accepts exactly three shapes:

```markdown
---
key: value                # scalar: bare string, quoted string, integer, true/false/yes/no
list_key:                 # string list
  - item one
  - item two
checks:                   # the one list-of-mappings
  - id: first-check
    question: "…"
---
```

Tabs are rejected. A list item's continuation lines must be indented **strictly
deeper** than the `- ` marker that opened them. Anything else raises `CompileError`.

### Fields

**Required on every file** (`schema.REQUIRED_FIELDS`): `id`, `locale`, `title`,
`summary`.

**Canonical-only** (`schema.CANONICAL_ONLY_FIELDS`) — these describe the guide, not
a translation of it: `category`, `kind`, `risk`, `status`, `last_reviewed`,
`related_guides`, `related_settings`, `diagnostics`, `actions`,
`common_problem_rank`.

**Per-locale optional** (`schema.LOCALISED_OPTIONAL_FIELDS`): `search_aliases`,
`stub`, `canonical`, `checks`, `translation_status`.

Any field not in one of those three sets **fails the build**. That is the point: a
mistyped key, or a `problem_guide:` that has escaped its check because of wrong
indentation, must be loud rather than silently ignored.

Closed vocabularies, all from `backend/help/schema.py`:

| Field | Allowed values |
| --- | --- |
| `locale` | `is`, `en` |
| `category` | `daily_operation`, `machines_telemetry`, `codes_reisa`, `scanner`, `hardware_network`, `admin_recovery`, `kiosk_display` |
| `kind` | `troubleshooting`, `procedure`, `concept`, `recovery` |
| `risk` | `low`, `medium`, `high` |
| `status` | `draft`, `review`, `published` |
| `translation_status` | `draft`, `review`, `published` |

`last_reviewed` is a required non-empty ISO date string on the canonical file.

`related_settings` entries must be real keys in `SETTING_SCHEMA`
(`backend/services/dev_admin_service.py`). A renamed or removed setting therefore
breaks the Help build, which is how the corpus stays honest about settings.

`diagnostics` entries must be in `compiler.DIAGNOSTIC_GROUPS`: `core`,
`machine.identity`, `machine.telemetry`, `machine.thresholds`, `machine.mapping`,
`settings.telemetry`, `settings.relay`, `settings.scanner`, `settings.provider`,
`provider.reisa`, `scanner.status`, `kiosk.state`. They scope what the support
report attaches for this guide.

`actions` must be in `compiler.KNOWN_ACTIONS`, currently `restart_backend` only.
There is no process control behind it; it is a label, not a button.

`common_problem_rank` is an integer. Ranked guides become the Common problems list
on the Help overview; unranked guides do not.

## Canonical and inheritance {#canonical-and-inheritance}

Exactly **one** locale per `id` carries `canonical: true`. That file owns every
canonical-only field. A second canonical for the same id, or none at all, fails the
build.

A translation may repeat a canonical-only field only if its value is *identical*
after normalisation (lists are sorted before comparison). Any real difference is
rejected with `translation overrides inherited field`. In practice: do not restate
`category`, `risk`, `related_guides` and friends in a translation — leave them out
and let them be inherited.

`checks` are per-locale because their prose is translated, but the validator
requires the **check `id` sequence to be identical** across full translations. The
same is true of H2 anchors. A translation that adds, drops, or reorders a check or a
section breaks the build.

## Translation gating {#translation-gating}

The canonical locale is the source text and is always treated as `published`. Every
other locale must say so explicitly:

```markdown
translation_status: published
```

A translation with no `translation_status` defaults to `draft`. Anything other than
`published` is **withheld from the manifest** and recorded in
`manifest["excluded_translations"]` — withheld, not lost, and asserted in tests so a
missing translation cannot go unnoticed. The operator then sees the canonical locale
instead.

> [!WARNING]
> Never flip a `translation_status` to `published` to make a check go green. It is a
> statement that a human has reviewed that translation's language. As of this
> writing the six Tier 1 Icelandic translations sit at `review` awaiting the
> maintainer's language review, and the Step 3 verification probe is *expected* to
> list them.

## Stubs {#stubs}

```markdown
---
id: tune-thresholds
locale: is
stub: true
translation_status: published
title: "…"
summary: "…"
search_aliases:
  - …
---
```

A stub is a **discovery shim**, not a short guide. Its body is not parsed and is not
emitted; the manifest carries only title, summary and aliases. Its job is to let an
Icelandic search for a familiar phrase find the guide, which then renders in the
canonical locale.

Write a stub when the guide exists and is useful but the full translation has not
been done. Give it generous `search_aliases`, because those aliases are the entire
reason the file exists. Do not put steps, causes, or reassurance in a stub body —
nobody will ever read it.

## Body Markdown {#body-markdown}

The body is parsed by mistune and then filtered against an allowlist. Any construct
not on the list raises `CompileError`; nothing is silently dropped.

Allowed blocks: paragraph, heading, ordered list, unordered list, fenced code block,
table (GFM pipe tables), block quote (rendered as a callout), and nested lists inside
list items.

Allowed inline: plain text, `**strong**`, `*emphasis*`, `` `code` ``, and links.

**Raw HTML is rejected**, inline and block. So are images, footnotes, definition
lists, setext headings with no anchor, and every other extension.

### H2 anchors are mandatory {#h2-anchors}

Every H2 must end with a stable anchor:

```markdown
## Possible causes {#causes}
```

The anchor must match `[a-z0-9][a-z0-9-]*`. H2s are what the body is split into —
each becomes one section in the manifest, and the anchor is the deep-link target in
`#help/<guide-id>/<anchor>`. An H2 without an anchor fails the build; anchors must be
unique within a guide, and identical across a guide's full translations.

H3 and lower are ordinary heading blocks inside the current section, and do not need
an anchor.

### `guide:` links {#guide-links}

Cross-reference another guide with the `guide:` scheme:

```markdown
read [All machines show available while telemetry is stale](guide:all-machines-available-telemetry-stale)
```

That becomes a `guide_link` inline the renderer turns into in-panel navigation. Any
other URL becomes an `external_link`. The validator walks every block, list item and
table cell: a `guide:` link, a `related_guides` entry, or a check's `problem_guide`
pointing at an id that does not exist **fails the build**. There are no dangling
cross-references in the Hub, by construction.

### Setting references {#setting-references}

A code span whose exact text is a key in `SETTING_SCHEMA` compiles to a
`setting_ref` inline rather than a `code` inline, and the panel renders it as a
first-class setting reference. So write `` `machine_reservation_minutes` `` and it
becomes a setting reference automatically; there is no separate syntax and no way to
force one for a key that does not exist.

### Callouts {#callouts}

A block quote is a callout. Its first line may carry a level marker, which is
stripped from the rendered text:

```markdown
> [!WARNING]
> Enabling this sends real commands to the relays.
```

Levels: `[!NOTE]`, `[!WARNING]`, `[!DANGER]`. A block quote with no marker is a
`note`.

## Checks {#checks}

`checks` drive the guided checklist panel and the support report. Each entry is a
mapping:

| Key | Meaning |
| --- | --- |
| `id` | required, non-empty, stable; the sequence must match across full translations |
| `question` | what the operator is being asked to determine |
| `look_for` | exactly where in the panel to look, named as the UI names it |
| `expected` | what a healthy system shows, and what a deviation means |
| `route` | which dev-admin tab to open: `overview`, `remote_control`, `diagnostics`, `settings` |
| `diagnostics` | one group name or a list of them, from the same closed set as the guide-level field |
| `problem_guide` | the guide to jump to when this check fails |

`route` values are the tab ids in `DevAdminShell.TABS` and are rendered verbatim, so
an invented tab id produces a dead link rather than a build error — check them by
hand. `diagnostics` and `problem_guide` *are* validated and will fail the build.

The operator's answers (`ok` / `problem` / `unsure` / `not_checked`,
`schema.CHECK_RESULTS`) are held in the browser and are only sent when they press
Send support report.

## Search aliases {#search-aliases}

`search_aliases` are the phrases an operator would actually type, in their own
words — "vélin er föst í notkun", "machine stuck in use", "scanner beeps but nothing
happens". They are indexed with the same folding as the body.

Folding, in `backend/help/search_index.py`: lowercase, then `þ→th`, `ð→d`, `æ→ae`,
`ö→o`, then strip remaining combining marks. Tokens shorter than four characters and
tokens in `STOPWORDS` are dropped from the index; matching in the browser is
prefix-based, which absorbs Icelandic definite forms, plurals and genitives without a
stemmer. Consequently an alias whose only distinguishing word is three letters long
will not be findable — give aliases at least one long, distinctive stem.

## Two trust classes {#two-trust-classes}

`docs/admin-guides/` compiles with `trust_class: "admin"` and is served only behind
the dev-admin Basic auth and the `dev_admin_enabled` kill switch.

`docs/public-help/` compiles with `trust_class: "public_bootstrap"`, is bundled into
the frontend, and is readable by **anyone who can load the page** — including during
a backend outage, which is the whole point of it. Its content rule is much stricter
and is enforced by a test
(`test_public_manifest_rejects_privileged_identifiers_entirely` in
`backend/tests/test_help_artifacts.py`): non-privileged physical checks, safe retry
guidance, and escalation language only. **No admin unlock or re-enable procedure, no
credential or API-key procedure, no hardware mapping, no relay enablement, no
privileged command.** Even *naming* `api_key`, `dev_admin_enabled`,
`backend_relay_enabled`, `sqlite3` or `.venv/bin/activate` fails the build.

The security boundary is the caller's choice of root plus that snapshot test — never
a flag inside a guide file. Do not add one.

## The corpus is derived from the runbooks, not a mirror of them {#derived-not-mirrored}

The runbooks under `docs/operations/runbooks/` are the engineering record: they may
name files and line numbers, quote `sqlite3` and `python -m`, and assume shell
access on the kiosk host. They are written for whoever maintains the system.

A Help guide is written for an operator standing in front of a kiosk with a customer
waiting, holding a tablet, with the dev-admin panel open and nothing else. It is
therefore a **derivation**, not a copy:

- **Start from the symptom, not the subsystem.** A guide's title is the complaint an
  operator would make. Its first section says when this is *not* the right guide.
- **Only name what the panel shows.** Field labels, tab names and banner text as
  they are rendered. If a fact is only observable over SSH, it does not belong in a
  guide — it belongs in a runbook, and the guide says who to escalate to.
- **No privileged commands.** No `sudo`, `sqlite3`, `curl`, `pip`, `python -m`,
  `.venv`, no credential-reading, no `localStorage`. The admin tier tolerates naming
  a setting; it does not tolerate a shell.
- **State the consequence before the action**, especially for anything that moves
  hardware or can take the kiosk offline.
- **Distinguish neighbouring guides by evidence, not by topic.** Two guides that
  would be resolved by the same observation should be one guide.
- **Verify against the code, not against the runbook.** Several runbook passages have
  been wrong. When a guide and a runbook disagree, read the source; then fix the
  runbook too.

When you change a guide's facts, check whether the corresponding runbook and
`docs/reference/settings-catalog.md` need the same correction.

## Compile and verify {#compile}

```bash
source .venv/bin/activate
python -m backend.help.cli            # rewrite both manifests
python -m backend.help.cli --check    # verify committed manifests are current; exit 1 if stale
```

`--check` recompiles in memory and diffs against what is on disk. It is the guard
against a guide edit landing without its regenerated manifest, so run it before
committing and treat a `STALE:` line as a failure.

The generated manifests **are committed**:

- `backend/help/generated/admin-help-manifest.json` — read at runtime by
  `backend/services/help_service.py`
- `frontend/src/generated/public-help-manifest.json` — imported statically by
  `frontend/src/public-help/PublicHelpPage.jsx`

Serialisation is deterministic (`indent=2, sort_keys=True, ensure_ascii=False`) and
the only volatile field is `build_id`, so a manifest diff is reviewable.

Then run the tests that cover content:

```bash
python -m pytest backend/tests/test_help_compiler.py backend/tests/test_help_validator.py \
                 backend/tests/test_help_artifacts.py backend/tests/test_help_api.py -q
```

## Where the guides are consumed

- Backend: `backend/services/help_service.py` loads the manifest once behind a
  failure boundary — a missing or malformed manifest disables Help alone and must
  never raise into scanning, telemetry, or machine control.
- API: `GET /api/dev_admin/help/status`, `GET /api/dev_admin/help/manifest`,
  `POST /api/dev_admin/support_report` — see
  [`../reference/api-reference.md`](../reference/api-reference.md).
- Frontend: `frontend/src/dev-admin/help/` (Help tab, drawer, checklist, search) and
  `frontend/src/public-help/` (the `/help` page).
- Deep links: `#help/<guide-id>` and `#help/<guide-id>/<anchor>`, parsed by
  `helpRouting.js`. An unknown id renders the not-found state; it does not fall back
  to the overview.
