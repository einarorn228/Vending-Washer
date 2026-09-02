# Admin Help Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline-capable, Icelandic-first Help Hub inside `/dev/admin` that lets a site operator either resolve a kiosk problem themselves or produce a precise escalation report for the developer.

**Architecture:** Markdown guides under two physically separate trust roots are compiled by one Python compiler into two deterministic, committed JSON manifests. Flask loads the admin manifest once behind a failure-isolated boundary and serves it over `require_dev_admin`; the browser fetches it once and does all search and rendering locally from a strict allowlisted block schema. A single server-owned, allowlisted support projection feeds the escalation report today and system-aware cards and AI later.

**Tech Stack:** Python 3.11, Flask 3.0.3, SQLAlchemy 2.0.35, React 18, Vite 7, mistune 3.3.4 (new, compile-time only), pytest.

**Spec:** `docs/superpowers/specs/2026-09-02-admin-help-hub-design.md`

## Global Constraints

- **Never render raw Markdown or HTML in the browser.** No `dangerouslySetInnerHTML` anywhere. Raw HTML in guide source is a compile error.
- **No filesystem path ever reaches an endpoint.** Runtime lookup is `manifest["guides"][guide_id]` — a dict key, never `open(path)`.
- **Help may fail; the backend may not fail because Help failed.** No import-time exception may escape the manifest loader.
- **Diagnostic groups are server-controlled.** The client sends `guide_id`, never group or field names. No `?groups=` parameter.
- **Secrets never appear** in guides, manifests, or reports. Presence booleans only (`reisa_token_configured: true`).
- **Manifests are committed, deterministic artifacts.** No timestamps, no nondeterministic ordering. A test recompiles and asserts byte equality.
- **Technical identifiers are never translated:** setting keys, machine IDs, API field names, error codes, IP addresses, Reisa action identifiers, commands, filenames.
- **Existing behaviour must not regress:** 96 pytest tests and the unittest runner stay green; kiosk flow untouched; `codes.db` and `frontend/.env` never modified by tests.
- Category vocabulary (frozen): `daily_operation`, `machines_telemetry`, `codes_reisa`, `scanner`, `hardware_network`, `admin_recovery`, `kiosk_display`.
- Kind vocabulary (frozen): `troubleshooting`, `procedure`, `concept`, `recovery`.
- Check result vocabulary (frozen): `ok`, `problem`, `unsure`, `not_checked`.
- Translation review vocabulary (frozen): `draft`, `review`, `published` — the per-locale
  `translation_status`, which is **never** the canonical `status`.
- **Machine diagnostic groups compose, never overwrite.** Machine data is keyed
  `data["machines"][<machine_id>][<subsection>]`.
- Block types (frozen): `paragraph`, `heading`, `ordered_list`, `unordered_list`, `code_block`, `table`, `callout`, `guide_link`, `external_link`. Inline: `text`, `strong`, `em`, `code`, `setting_ref`, `guide_link`, `external_link`.

## Execution protocol (approved 2026-09-02)

- **Mode:** subagent-driven development — a fresh subagent per task, each result reviewed
  before acceptance. Low-risk tasks continue after review passes.
- **Hard review checkpoints — stop and wait for explicit maintainer approval before the next
  dependent layer:** Task 5 (compiler / inheritance / translation filtering), Task 8
  (manifest loading and provenance), Task 9 (support projection), Task 10 (authenticated
  API surface), Task 15 (Help UI + contextual integration), Task 17 (guide corpus). Never
  batch two of these together.
- **Branch:** all work on a dedicated `help-hub` branch cut from the reviewed baseline
  commit (Task 0). Commits scoped to plan tasks only; never absorb unrelated dirty-tree
  changes.
- **Interface mismatch rule:** if a task finds the live repository differs from what the
  plan assumes, stop that task and correct the plan deliberately. No compatibility hacks.
- **Safety, unchanged from the pre-merge hardening:** tests never touch the real `codes.db`
  or `frontend/.env`; `backend_relay_enabled` stays `false` throughout; no hardware, no
  credential rotation, no Pi runtime changes, no merge or push unless explicitly requested.
- **Tier 1 Icelandic:** subagents may draft the six Tier 1 translations but must leave
  `translation_status: review`. Only the maintainer flips it to `published`. Working around
  the validator to ship them is forbidden.

---

## Parser decision (settled — do not revisit during implementation)

**Chosen: `mistune` 3.3.4.** Measured in a throwaway venv against `markdown-it-py` 4.2.0 on a representative Icelandic guide containing a `{#anchor}` heading, `> [!WARNING]` callout, nested lists, a table, a fenced block, and both link kinds — plus a deliberately malformed document.

| Criterion | mistune 3.3.4 | markdown-it-py 4.2.0 |
|---|---|---|
| Runtime dependencies | **0** | 1 (`mdurl`) |
| AST shape | **Nested tree**, 18 node types | Flat open/close stream, 26 token types |
| `{#anchor}` capture | Not native — 1-line regex | **Also not native** — `attrs_plugin`, `attrs_plugin(spans=True)` and `attrs_block_plugin` all returned `attrs=None` |
| Malformed input | No raise | No raise |
| Icelandic/Unicode | Correct | Correct |
| Tables / nested lists / fences | Correct | Correct |

The deciding factor: neither library captures trailing heading attributes, so we extract `{#anchor}` with our own regex either way — which erases markdown-it-py's plugin-ecosystem advantage. What remains is that **mistune yields a nested AST that maps directly onto our block schema by recursion**, whereas markdown-it-py yields a flat token stream we would have to reassemble into a tree before converting. Fewer moving parts, less code, fewer edge cases, and zero transitive dependencies.

markdown-it-py's one genuine edge is certified CommonMark strictness. That matters for arbitrary third-party Markdown; it does not matter here, because we author every guide, the syntax subset is small, and **the compiler rejects any node type it does not explicitly map** — unexpected syntax becomes a build error rather than silently vanishing. That rejection rule, not the parser, is the predictability guarantee.

---

## File Structure

**New — compiler and validator** (`backend/help/`, a package so `pytest` imports it directly):

| File | Responsibility |
|---|---|
| `backend/help/__init__.py` | package marker |
| `backend/help/schema.py` | frozen vocabularies, required/optional field sets, `SCHEMA_VERSION` |
| `backend/help/frontmatter.py` | split YAML-ish frontmatter from body; no PyYAML dependency |
| `backend/help/blocks.py` | mistune AST → strict block schema; unknown node → `CompileError` |
| `backend/help/search_index.py` | Icelandic folding, tokenisation, per-guide index records |
| `backend/help/compiler.py` | `compile_help(root, trust_class)` → manifest dict |
| `backend/help/validator.py` | cross-guide rules (IDs, anchors, parity, links, settings keys) |
| `backend/help/cli.py` | `python -m backend.help.cli` writes both artifacts |

**New — runtime:**

| File | Responsibility |
|---|---|
| `backend/services/help_service.py` | failure-isolated manifest load + accessors |
| `backend/services/support_service.py` | allowlisted diagnostic groups, redaction, report assembly |

**New — artifacts (committed):**

| File | Responsibility |
|---|---|
| `backend/help/generated/admin-help-manifest.json` | authenticated corpus |
| `frontend/src/generated/public-help-manifest.json` | public bootstrap corpus |

**New — frontend** (`frontend/src/dev-admin/help/`):

| File | Responsibility |
|---|---|
| `helpRouting.js` | parse/format `#help/...` hashes |
| `useHelpManifest.js` | fetch once, cache, expose load error |
| `helpSearch.js` | fold, tokenise, score, rank |
| `helpStrings.js` | Icelandic + English UI chrome |
| `BlockRenderer.jsx` | block schema → React elements |
| `GuideView.jsx` | one guide: header, fallback notice, blocks, checklist, related |
| `ChecklistPanel.jsx` | check results state |
| `SupportReportButton.jsx` | request + copy report |
| `HelpPanel.jsx` | full tab: search, Common Problems, categories |
| `HelpDrawer.jsx` | contextual overlay |
| `ContextualHelpLink.jsx` | the `?` trigger used at six sites |
| `frontend/src/public-help/PublicHelpPage.jsx` | public bootstrap tier at `/help` |

**Modified:**

| File | Change |
|---|---|
| `backend/controllers/dev_admin_api.py` | three new routes |
| `backend/models/__init__.py` | none — listed only to confirm no change |
| `frontend/src/dev-admin/DevAdminPage.jsx` | help tab, drawer state, hash routing |
| `frontend/src/dev-admin/DevAdminShell.jsx` | `help` tab entry, banner help link |
| `frontend/src/dev-admin/api.js` | help + support-report clients |
| `frontend/src/App.jsx` | `/help` public route |
| `frontend/src/dev-admin/components/{DiagnosticsPanel,SettingsPanel,MachineDetailDrawer,SecuritySettingsPanel,DangerZonePanel}.jsx` | contextual `?` links |
| `frontend/src/dev-admin/styles/dev-admin.css` | help styles |
| `requirements.txt` | `mistune==3.3.4` |

**Content:** `docs/admin-guides/{en,is}/<category>/<guide-id>.md`, `docs/public-help/<guide-id>.md`.

---

### Task 0 (PREREQUISITE — requires human approval before any task runs)

**This is not an implementation task. Do not perform it automatically.**

Every task below ends in `git commit`. The working tree currently holds **47 changed paths**
of approved-but-uncommitted dev-admin work (the settings/diagnostics/audit/atomic-save feature
plus the pre-merge hardening). If subagents start committing on top of that, Help Hub commits
and dev-admin commits interleave irreversibly, and any task revert takes unrelated work with
it.

Execution must not begin until one of these is done **by the maintainer**:

- **Option A — baseline commit on `UI-changes`.** Review the existing 47 paths, commit them as
  one reviewed baseline, then run the plan on a clean tree. Simplest; keeps one branch.
- **Option B — dedicated branch off the baseline.** Make the baseline commit, branch
  `help-hub` from it, run the plan there. Keeps Help Hub reviewable as an isolated diff.
- **Option C — git worktree.** Baseline commit, then a worktree containing exactly the
  approved state. Strongest isolation; leaves `UI-changes` untouched during development.

Recommended: **Option B**. The Help Hub is a self-contained feature that deserves its own
reviewable diff, and it keeps the pre-merge-verified dev-admin state intact as a known-good
commit to fall back to.

Verify before starting:

```bash
git status --short          # expect: empty
git log --oneline -1        # expect: the reviewed baseline commit
sha256sum codes.db frontend/.env   # record; must be unchanged at the end
```

**STOP.** Do not create the baseline commit as part of executing this plan. Get explicit
approval, let the maintainer make it, then start at Task 1.

---

### Task 1: Frozen schema vocabularies

**Files:**
- Create: `backend/help/__init__.py`, `backend/help/schema.py`
- Test: `backend/tests/test_help_schema.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SCHEMA_VERSION: int`, `CATEGORIES: frozenset[str]`, `KINDS: frozenset[str]`, `RISKS: frozenset[str]`, `STATUSES: frozenset[str]`, `CHECK_RESULTS: frozenset[str]`, `BLOCK_TYPES: frozenset[str]`, `INLINE_TYPES: frozenset[str]`, `REQUIRED_FIELDS: frozenset[str]`, `CANONICAL_ONLY_FIELDS: frozenset[str]`, `LOCALISED_OPTIONAL_FIELDS: frozenset[str]`, `LOCALES: tuple[str, ...]`, `DEFAULT_LOCALE: str`, `class CompileError(Exception)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_help_schema.py
import unittest

from backend.help import schema


class HelpSchemaTests(unittest.TestCase):
    def test_vocabularies_are_frozen_and_complete(self):
        self.assertEqual(schema.SCHEMA_VERSION, 1)
        self.assertEqual(schema.LOCALES, ("is", "en"))
        self.assertEqual(schema.DEFAULT_LOCALE, "is")
        self.assertEqual(
            schema.CATEGORIES,
            frozenset({
                "daily_operation", "machines_telemetry", "codes_reisa", "scanner",
                "hardware_network", "admin_recovery", "kiosk_display",
            }),
        )
        self.assertEqual(
            schema.KINDS,
            frozenset({"troubleshooting", "procedure", "concept", "recovery"}),
        )
        self.assertEqual(
            schema.CHECK_RESULTS,
            frozenset({"ok", "problem", "unsure", "not_checked"}),
        )

    def test_translation_status_is_separate_from_canonical_status(self):
        self.assertEqual(
            schema.TRANSLATION_STATUSES, frozenset({"draft", "review", "published"})
        )
        self.assertIn("translation_status", schema.LOCALISED_OPTIONAL_FIELDS)
        self.assertNotIn("translation_status", schema.CANONICAL_ONLY_FIELDS)
        self.assertIn("status", schema.CANONICAL_ONLY_FIELDS)

    def test_field_sets_do_not_overlap(self):
        self.assertFalse(schema.REQUIRED_FIELDS & schema.CANONICAL_ONLY_FIELDS)
        self.assertFalse(schema.REQUIRED_FIELDS & schema.LOCALISED_OPTIONAL_FIELDS)
        self.assertFalse(schema.CANONICAL_ONLY_FIELDS & schema.LOCALISED_OPTIONAL_FIELDS)

    def test_compile_error_is_an_exception(self):
        with self.assertRaises(schema.CompileError):
            raise schema.CompileError("boom")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.help'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/help/__init__.py
"""Admin Help Hub: compiler, validator, and content schema."""
```

```python
# backend/help/schema.py
"""Frozen vocabularies for the Help Hub content model.

These are deliberately closed sets. Adding a value is a source change plus a test
change, which is the point: content must not invent categories, kinds, or block
types that the renderer has never seen.
"""

SCHEMA_VERSION = 1

LOCALES = ("is", "en")
DEFAULT_LOCALE = "is"

CATEGORIES = frozenset({
    "daily_operation", "machines_telemetry", "codes_reisa", "scanner",
    "hardware_network", "admin_recovery", "kiosk_display",
})
KINDS = frozenset({"troubleshooting", "procedure", "concept", "recovery"})
RISKS = frozenset({"low", "medium", "high"})
STATUSES = frozenset({"draft", "review", "published"})
CHECK_RESULTS = frozenset({"ok", "problem", "unsure", "not_checked"})

BLOCK_TYPES = frozenset({
    "paragraph", "heading", "ordered_list", "unordered_list",
    "code_block", "table", "callout", "guide_link", "external_link",
})
INLINE_TYPES = frozenset({
    "text", "strong", "em", "code", "setting_ref", "guide_link", "external_link",
})

# `STATUSES` above is the canonical publication state of the guide as a whole.
# Review state of ONE translation. Deliberately separate from the canonical `status`:
# a guide can be published while its Icelandic translation is still being reviewed.
TRANSLATION_STATUSES = frozenset({"draft", "review", "published"})

REQUIRED_FIELDS = frozenset({"id", "locale", "title", "summary"})
CANONICAL_ONLY_FIELDS = frozenset({
    "category", "kind", "risk", "status", "last_reviewed",
    "related_guides", "related_settings", "diagnostics", "actions",
    "common_problem_rank",
})
LOCALISED_OPTIONAL_FIELDS = frozenset({
    "search_aliases", "stub", "canonical", "checks", "translation_status",
})


class CompileError(Exception):
    """Raised for any content defect. Always fails the build; never swallowed."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_schema.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/help/__init__.py backend/help/schema.py backend/tests/test_help_schema.py
git commit -m "feat(help): add frozen Help Hub content vocabularies"
```

---

### Task 2: Frontmatter parsing without a YAML dependency

**Files:**
- Create: `backend/help/frontmatter.py`
- Test: `backend/tests/test_help_frontmatter.py`

**Interfaces:**
- Consumes: `backend.help.schema.CompileError`.
- Produces: `split_frontmatter(text: str) -> tuple[dict, str]` returning `(metadata, body)`. Values are `str`, `bool`, `int`, `list[str]`, or `list[dict]` (for `checks`).

Guide frontmatter uses a deliberately small subset — scalars, string lists, and one list-of-mappings (`checks`) — so a 60-line parser removes a dependency and, more importantly, rejects anything outside the subset instead of accepting arbitrary YAML.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_help_frontmatter.py
import unittest

from backend.help.frontmatter import split_frontmatter
from backend.help.schema import CompileError


class FrontmatterTests(unittest.TestCase):
    def test_parses_scalars_lists_and_body(self):
        meta, body = split_frontmatter(
            "---\n"
            "id: machine-unavailable\n"
            "locale: is\n"
            "title: Vélin sýnist upptekin\n"
            "canonical: false\n"
            "common_problem_rank: 1\n"
            "related_guides:\n"
            "  - tune-thresholds\n"
            "  - no-telemetry\n"
            "---\n"
            "\n## Efni {#body}\n"
        )
        self.assertEqual(meta["id"], "machine-unavailable")
        self.assertEqual(meta["title"], "Vélin sýnist upptekin")
        self.assertIs(meta["canonical"], False)
        self.assertEqual(meta["common_problem_rank"], 1)
        self.assertEqual(meta["related_guides"], ["tune-thresholds", "no-telemetry"])
        self.assertIn("## Efni {#body}", body)

    def test_parses_checks_list_of_mappings(self):
        meta, _ = split_frontmatter(
            "---\n"
            "id: g\n"
            "locale: en\n"
            "title: T\n"
            "summary: S\n"
            "checks:\n"
            "  - id: telemetry-enabled\n"
            "    question: Is telemetry on?\n"
            "    route: diagnostics\n"
            "  - id: current-reading\n"
            "    question: What is the reading?\n"
            "---\n"
            "body\n"
        )
        self.assertEqual(len(meta["checks"]), 2)
        self.assertEqual(meta["checks"][0]["id"], "telemetry-enabled")
        self.assertEqual(meta["checks"][1]["question"], "What is the reading?")

    def test_missing_frontmatter_is_a_compile_error(self):
        with self.assertRaises(CompileError):
            split_frontmatter("# just a heading\n")

    def test_unterminated_frontmatter_is_a_compile_error(self):
        with self.assertRaises(CompileError):
            split_frontmatter("---\nid: g\n")

    def test_tab_indentation_is_rejected(self):
        with self.assertRaises(CompileError):
            split_frontmatter("---\nid: g\nrelated_guides:\n\t- a\n---\nbody\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_frontmatter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.help.frontmatter'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/help/frontmatter.py
"""Minimal frontmatter parser for the Help Hub subset.

Supports exactly what guides are allowed to use: `key: value` scalars, `- item`
string lists, and one list-of-mappings (`checks`). Anything else raises, which is
the intended behaviour -- guides must not carry arbitrary YAML.
"""

from backend.help.schema import CompileError

DELIMITER = "---"
_TRUE = {"true", "yes"}
_FALSE = {"false", "no"}


def _coerce(raw: str):
    text = raw.strip()
    if text.lower() in _TRUE:
        return True
    if text.lower() in _FALSE:
        return False
    if text and (text.lstrip("-").isdigit()):
        return int(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        return text[1:-1]
    return text


def split_frontmatter(text: str):
    lines = text.splitlines()
    if not lines or lines[0].strip() != DELIMITER:
        raise CompileError("file must start with a '---' frontmatter block")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == DELIMITER)
    except StopIteration:
        raise CompileError("frontmatter block is not terminated by '---'")

    meta = {}
    key = None            # current list-valued key
    entry = None          # current mapping inside a list-of-mappings
    for lineno, line in enumerate(lines[1:end], start=2):
        if "\t" in line:
            raise CompileError(f"line {lineno}: tabs are not allowed in frontmatter")
        if not line.strip():
            continue
        stripped = line.strip()

        if stripped.startswith("- "):
            if key is None:
                raise CompileError(f"line {lineno}: list item outside any key")
            item = stripped[2:].strip()
            if ":" in item and not item.startswith(("http://", "https://")):
                field, _, value = item.partition(":")
                entry = {field.strip(): _coerce(value)}
                meta[key].append(entry)
            else:
                entry = None
                meta[key].append(_coerce(item))
            continue

        if line.startswith(("    ", "  ")) and entry is not None and ":" in stripped:
            field, _, value = stripped.partition(":")
            entry[field.strip()] = _coerce(value)
            continue

        if ":" not in stripped:
            raise CompileError(f"line {lineno}: expected 'key: value'")
        raw_key, _, raw_value = stripped.partition(":")
        key = raw_key.strip()
        entry = None
        if raw_value.strip() == "":
            meta[key] = []
        else:
            meta[key] = _coerce(raw_value)
            key = None

    return meta, "\n".join(lines[end + 1:])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_frontmatter.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/help/frontmatter.py backend/tests/test_help_frontmatter.py
git commit -m "feat(help): parse guide frontmatter without a YAML dependency"
```

---

### Task 3: Markdown body → strict block schema

**Files:**
- Create: `backend/help/blocks.py`
- Modify: `requirements.txt`
- Test: `backend/tests/test_help_blocks.py`

**Interfaces:**
- Consumes: `schema.CompileError`, `schema.BLOCK_TYPES`, `schema.INLINE_TYPES`.
- Produces: `parse_body(markdown: str, known_settings: set[str]) -> list[dict]` returning section dicts `{"anchor": str, "heading": str, "blocks": [...]}`; `ANCHOR_RE`.

Content before the first H2 goes into a section with `anchor: None` (the guide intro). `> [!WARNING]` / `> [!NOTE]` / `> [!DANGER]` blockquotes become `callout` blocks. Inline `` `code` `` whose text is a known setting key becomes `setting_ref`. Links with a `guide:` scheme become `guide_link`. **Any mistune node type not explicitly mapped raises `CompileError`.**

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_help_blocks.py
import unittest

from backend.help.blocks import parse_body
from backend.help.schema import BLOCK_TYPES, CompileError

SETTINGS = {"telemetry_enabled", "backend_relay_enabled"}


class BlockParsingTests(unittest.TestCase):
    def test_sections_split_on_h2_anchors(self):
        sections = parse_body(
            "Intro paragraph.\n\n"
            "## Athugaðu fjarmælingar {#check-telemetry}\n\n"
            "Fyrsta málsgrein.\n\n"
            "## Næsta skref {#next-step}\n\n"
            "Önnur málsgrein.\n",
            SETTINGS,
        )
        self.assertEqual([s["anchor"] for s in sections], [None, "check-telemetry", "next-step"])
        self.assertEqual(sections[1]["heading"], "Athugaðu fjarmælingar")

    def test_all_emitted_block_types_are_allowlisted(self):
        sections = parse_body(
            "## S {#s}\n\n"
            "Para.\n\n"
            "- a\n- b\n\n"
            "1. one\n2. two\n\n"
            "```bash\ncmd\n```\n\n"
            "| A | B |\n|---|---|\n| 1 | 2 |\n",
            SETTINGS,
        )
        emitted = {b["type"] for b in sections[0]["blocks"]}
        self.assertTrue(emitted <= BLOCK_TYPES, f"unexpected: {emitted - BLOCK_TYPES}")
        self.assertIn("code_block", emitted)
        self.assertIn("table", emitted)
        self.assertIn("ordered_list", emitted)
        self.assertIn("unordered_list", emitted)

    def test_table_header_and_rows_have_the_right_shape(self):
        sections = parse_body("## S {#s}\n\n| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |\n", SETTINGS)
        table = next(b for b in sections[0]["blocks"] if b["type"] == "table")
        self.assertEqual(len(table["header"]), 2, "header must be one row of two cells")
        self.assertEqual([c[0]["text"] for c in table["header"]], ["A", "B"])
        self.assertEqual(len(table["rows"]), 2)
        self.assertEqual([c[0]["text"] for c in table["rows"][1]], ["3", "4"])

    def test_known_setting_key_becomes_setting_ref(self):
        sections = parse_body("## S {#s}\n\nTurn on `telemetry_enabled` and `whatever`.\n", SETTINGS)
        inlines = sections[0]["blocks"][0]["inlines"]
        kinds = {(i["type"], i.get("value") or i.get("text")) for i in inlines}
        self.assertIn(("setting_ref", "telemetry_enabled"), kinds)
        self.assertIn(("code", "whatever"), kinds)

    def test_guide_scheme_link_becomes_guide_link(self):
        sections = parse_body("## S {#s}\n\nSee [thresholds](guide:tune-thresholds).\n", SETTINGS)
        inlines = sections[0]["blocks"][0]["inlines"]
        links = [i for i in inlines if i["type"] == "guide_link"]
        self.assertEqual(links[0]["guide_id"], "tune-thresholds")

    def test_alert_blockquote_becomes_callout(self):
        sections = parse_body("## S {#s}\n\n> [!WARNING]\n> Careful.\n", SETTINGS)
        callouts = [b for b in sections[0]["blocks"] if b["type"] == "callout"]
        self.assertEqual(callouts[0]["level"], "warning")

    def test_raw_html_is_a_compile_error(self):
        with self.assertRaises(CompileError):
            parse_body("## S {#s}\n\n<script>alert(1)</script>\n", SETTINGS)

    def test_h2_without_anchor_is_a_compile_error(self):
        with self.assertRaises(CompileError):
            parse_body("## No anchor here\n\ntext\n", SETTINGS)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_blocks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.help.blocks'`

- [ ] **Step 3: Add the dependency, then implement**

Append `mistune==3.3.4` to `requirements.txt`, then `pip install mistune==3.3.4`.

```python
# backend/help/blocks.py
"""Convert guide Markdown into our strict, allowlisted block schema.

mistune parses; this module decides what is allowed to exist. Any node type we do
not explicitly map raises CompileError, so unsupported syntax fails the build
instead of silently disappearing from a guide an operator is relying on.
"""

import re

import mistune

from backend.help.schema import CompileError

ANCHOR_RE = re.compile(r"\s*\{#([a-z0-9][a-z0-9-]*)\}\s*$")
_ALERT_RE = re.compile(r"^\[!(NOTE|WARNING|DANGER)\]\s*$", re.IGNORECASE)
_GUIDE_SCHEME = "guide:"

_markdown = mistune.create_markdown(renderer=None, plugins=["table"])


def _raw(nodes):
    return "".join(n.get("raw", "") or _raw(n.get("children", [])) for n in nodes)


def _inlines(nodes, known_settings):
    out = []
    for node in nodes:
        kind = node.get("type")
        if kind == "text":
            out.append({"type": "text", "text": node.get("raw", "")})
        elif kind == "softbreak":
            out.append({"type": "text", "text": " "})
        elif kind == "codespan":
            value = node.get("raw", "")
            out.append(
                {"type": "setting_ref", "value": value}
                if value in known_settings
                else {"type": "code", "text": value}
            )
        elif kind == "strong":
            out.append({"type": "strong", "inlines": _inlines(node.get("children", []), known_settings)})
        elif kind == "emphasis":
            out.append({"type": "em", "inlines": _inlines(node.get("children", []), known_settings)})
        elif kind == "link":
            url = (node.get("attrs") or {}).get("url", "")
            text = _raw(node.get("children", []))
            if url.startswith(_GUIDE_SCHEME):
                out.append({"type": "guide_link", "guide_id": url[len(_GUIDE_SCHEME):], "text": text})
            else:
                out.append({"type": "external_link", "url": url, "text": text})
        elif kind in ("block_html", "inline_html"):
            raise CompileError("raw HTML is not allowed in guide content")
        else:
            raise CompileError(f"unsupported inline node: {kind!r}")
    return out


def _list_items(node, known_settings):
    items = []
    for item in node.get("children", []):
        blocks = []
        for child in item.get("children", []):
            if child.get("type") in ("block_text", "paragraph"):
                blocks.append({"type": "paragraph",
                               "inlines": _inlines(child.get("children", []), known_settings)})
            elif child.get("type") == "list":
                blocks.append(_block(child, known_settings))
            else:
                raise CompileError(f"unsupported list child: {child.get('type')!r}")
        items.append(blocks)
    return items


def _block(node, known_settings):
    kind = node.get("type")
    if kind == "paragraph":
        return {"type": "paragraph", "inlines": _inlines(node.get("children", []), known_settings)}
    if kind == "block_code":
        return {"type": "code_block",
                "language": (node.get("attrs") or {}).get("info") or "",
                "text": node.get("raw", "").rstrip("\n")}
    if kind == "list":
        ordered = bool((node.get("attrs") or {}).get("ordered"))
        return {"type": "ordered_list" if ordered else "unordered_list",
                "items": _list_items(node, known_settings)}
    if kind == "table":
        # mistune 3 shape (verified): table_head holds table_cell nodes DIRECTLY,
        # while table_body -> table_row -> table_cell. Treating the head like a
        # body would emit one empty "row" per header cell.
        header, rows = [], []
        for part in node.get("children", []):
            if part.get("type") == "table_head":
                header = [_inlines(c.get("children", []), known_settings)
                          for c in part.get("children", [])]
            elif part.get("type") == "table_body":
                for row in part.get("children", []):
                    rows.append([_inlines(c.get("children", []), known_settings)
                                 for c in row.get("children", [])])
            else:
                raise CompileError(f"unsupported table part: {part.get('type')!r}")
        return {"type": "table", "header": header, "rows": rows}
    if kind == "block_quote":
        children = node.get("children", [])
        level = "note"
        if children:
            first = _raw(children[0].get("children", [])).strip()
            match = _ALERT_RE.match(first.splitlines()[0] if first else "")
            if match:
                level = match.group(1).lower()
        blocks = []
        for child in children:
            block = _block(child, known_settings)
            if block["type"] == "paragraph":
                block["inlines"] = [
                    i for i in block["inlines"]
                    if not (i["type"] == "text" and _ALERT_RE.match(i["text"].strip()))
                ]
                if not block["inlines"]:
                    continue
            blocks.append(block)
        return {"type": "callout", "level": level, "blocks": blocks}
    if kind in ("block_html", "inline_html"):
        raise CompileError("raw HTML is not allowed in guide content")
    raise CompileError(f"unsupported block node: {kind!r}")


def parse_body(markdown_text, known_settings):
    ast = _markdown(markdown_text)
    sections = [{"anchor": None, "heading": None, "blocks": []}]
    for node in ast:
        kind = node.get("type")
        if kind == "blank_line":
            continue
        if kind == "heading":
            level = (node.get("attrs") or {}).get("level", 1)
            text = _raw(node.get("children", []))
            if level == 2:
                match = ANCHOR_RE.search(text)
                if not match:
                    raise CompileError(f"H2 heading needs a stable anchor: {text!r}")
                sections.append({"anchor": match.group(1),
                                 "heading": text[: match.start()].strip(),
                                 "blocks": []})
                continue
            sections[-1]["blocks"].append(
                {"type": "heading", "level": level, "text": ANCHOR_RE.sub("", text).strip()}
            )
            continue
        sections[-1]["blocks"].append(_block(node, known_settings))
    if not sections[0]["blocks"]:
        sections.pop(0)
    return sections
```

> **Corrections applied during execution (Task 3 is complete; the committed
> `backend/help/blocks.py` at `539ead4` is authoritative over the snippet above).** Three
> defects in the snippet were found by implementation and review and fixed in the shipped code:
> 1. `_raw()` returned `""` for `softbreak` nodes (they carry neither `raw` nor `children`),
>    which concatenated `[!WARNING]` with the following line and broke callout detection.
>    Shipped code maps `softbreak` to `"\n"`.
> 2. `blank_line` nodes appear inside `list_item` (multi-paragraph items) and `block_quote`
>    (blank separator after the marker); the snippet only skipped them at top level and so
>    raised a spurious `CompileError`. Shipped code skips `blank_line` in exactly those two
>    containers and nowhere else — the catch-all rejection of unmapped nodes is unchanged.
> 3. Stripping the `[!…]` marker left the softbreak-derived `" "` inline; shipped code also
>    drops a leading whitespace-only text inline from the callout body.
>
> The test file gained `test_table_header_and_rows_have_the_right_shape`,
> `test_multi_paragraph_list_item_parses`, `test_callout_with_blank_separator_line_parses`
> and `test_callout_body_has_no_marker_or_stray_whitespace` (11 tests total).

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_blocks.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/help/blocks.py backend/tests/test_help_blocks.py requirements.txt
git commit -m "feat(help): compile guide Markdown into a strict block schema"
```

---

### Task 4: Icelandic search index generation

**Files:**
- Create: `backend/help/search_index.py`
- Test: `backend/tests/test_help_search_index.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `fold(text: str) -> str`, `tokenise(text: str) -> list[str]`, `build_index_record(locale_payload: dict, sections: list[dict]) -> dict` with keys `title`, `aliases`, `summary`, `headings`, `body` (each a deduplicated token list), `STOPWORDS: frozenset[str]`, `MIN_TOKEN_LEN: int`.

The identical `fold`/`tokenise` logic is reimplemented in `helpSearch.js` (Task 12); Task 12's test asserts parity against fixtures generated here.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_help_search_index.py
import unittest

from backend.help.search_index import MIN_TOKEN_LEN, build_index_record, fold, tokenise


class FoldingTests(unittest.TestCase):
    def test_folds_icelandic_to_ascii(self):
        self.assertEqual(fold("Þvottavél"), "thvottavel")
        self.assertEqual(fold("þurrkari"), "thurrkari")
        self.assertEqual(fold("aðgengilegur"), "adgengilegur")
        self.assertEqual(fold("Ræsir"), "raesir")
        self.assertEqual(fold("Ö"), "o")

    def test_ascii_transliteration_matches_folded_icelandic(self):
        self.assertEqual(fold("thvottavel"), fold("þvottavel"))

    def test_tokenise_drops_punctuation_and_short_tokens(self):
        self.assertEqual(tokenise("Þvottavélin virkar ekki!"), ["thvottavelin", "virkar", "ekki"])

    def test_min_token_len_is_four(self):
        self.assertEqual(MIN_TOKEN_LEN, 4)


class IndexRecordTests(unittest.TestCase):
    def test_builds_per_field_token_lists(self):
        record = build_index_record(
            {"title": "Vélin sýnist upptekin", "summary": "Þvottavél laus",
             "search_aliases": ["washer", "þvottavél"]},
            [{"anchor": "check-telemetry", "heading": "Athugaðu fjarmælingar",
              "blocks": [{"type": "paragraph",
                          "inlines": [{"type": "text", "text": "Fjarmæling verður að vera virk"}]}]}],
        )
        self.assertIn("velin", record["title"])
        self.assertIn("thvottavel", record["aliases"])
        self.assertIn("athugadu", record["headings"])
        self.assertIn("fjarmaeling", record["body"])
        self.assertEqual(record["body"], sorted(set(record["body"])))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_search_index.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.help.search_index'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/help/search_index.py
"""Search tokens for the Help Hub.

Icelandic inflection is suffixal, so the stem is stable at the front. Folding plus
prefix matching (done in the browser) absorbs definite forms, plurals, genitives and
head-initial compounds without a stemmer. This module only produces the folded
tokens; scoring lives in frontend/src/dev-admin/help/helpSearch.js.
"""

import re
import unicodedata

MIN_TOKEN_LEN = 4

_FOLD_MAP = {"þ": "th", "ð": "d", "æ": "ae", "ö": "o"}
_TOKEN_RE = re.compile(r"[a-z0-9]+")

STOPWORDS = frozenset({
    "og", "eda", "sem", "thad", "their", "ekki", "vera", "verdur", "thegar", "meira",
    "the", "and", "for", "with", "that", "this", "from", "your", "should", "when",
})


def fold(text):
    lowered = (text or "").lower()
    expanded = "".join(_FOLD_MAP.get(char, char) for char in lowered)
    decomposed = unicodedata.normalize("NFD", expanded)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def tokenise(text):
    return [token for token in _TOKEN_RE.findall(fold(text)) if len(token) >= 2]


def _significant(text):
    return sorted({t for t in tokenise(text) if len(t) >= MIN_TOKEN_LEN and t not in STOPWORDS})


def _inline_text(inlines):
    parts = []
    for inline in inlines or []:
        if "text" in inline:
            parts.append(inline["text"])
        if "value" in inline:
            parts.append(inline["value"])
        if "inlines" in inline:
            parts.append(_inline_text(inline["inlines"]))
    return " ".join(parts)


def _block_text(blocks):
    parts = []
    for block in blocks or []:
        kind = block.get("type")
        if kind in ("paragraph", "heading"):
            parts.append(block.get("text") or _inline_text(block.get("inlines")))
        elif kind in ("ordered_list", "unordered_list"):
            for item in block.get("items", []):
                parts.append(_block_text(item))
        elif kind == "callout":
            parts.append(_block_text(block.get("blocks")))
        elif kind == "table":
            for row in [block.get("header", [])] + block.get("rows", []):
                for cell in row:
                    parts.append(_inline_text(cell))
    return " ".join(p for p in parts if p)


def build_index_record(locale_payload, sections):
    return {
        "title": _significant(locale_payload.get("title", "")),
        "summary": _significant(locale_payload.get("summary", "")),
        "aliases": _significant(" ".join(locale_payload.get("search_aliases") or [])),
        "headings": _significant(" ".join(s.get("heading") or "" for s in sections or [])),
        "body": _significant(" ".join(_block_text(s.get("blocks")) for s in sections or [])),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_search_index.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/help/search_index.py backend/tests/test_help_search_index.py
git commit -m "feat(help): generate folded Icelandic search tokens"
```

---

### Task 5: Compiler — assemble a deterministic manifest

**Files:**
- Create: `backend/help/compiler.py`
- Test: `backend/tests/test_help_compiler.py`

**Interfaces:**
- Consumes: `frontmatter.split_frontmatter`, `blocks.parse_body`, `search_index.build_index_record`, `schema.*`.
- Produces: `compile_help(root: Path, trust_class: str, known_settings: set[str], build_id: str | None) -> dict`; `DIAGNOSTIC_GROUPS: frozenset[str]`; `KNOWN_ACTIONS: frozenset[str]`.

Determinism: every mapping is emitted with sorted keys and every list in a stable declared order; no timestamp is written.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_help_compiler.py
import json
import tempfile
import unittest
from pathlib import Path

from backend.help.compiler import compile_help
from backend.help.schema import SCHEMA_VERSION, CompileError

EN = """---
id: machine-unavailable
locale: en
canonical: true
title: Machine shows unavailable
summary: The machine is idle but the kiosk shows it as unavailable.
category: machines_telemetry
kind: troubleshooting
risk: medium
status: published
last_reviewed: 2026-09-02
common_problem_rank: 1
search_aliases:
  - washer
diagnostics:
  - machine.telemetry
related_settings:
  - telemetry_enabled
---

## Check telemetry {#check-telemetry}

Compare `telemetry_enabled` with the reading.
"""

IS_STUB = """---
id: machine-unavailable
locale: is
title: Vélin sýnist upptekin
summary: Vélin er laus en skjárinn sýnir hana upptekna.
stub: true
search_aliases:
  - þvottavél
---
"""

# The reviewed variant: this is what actually ships.
IS_STUB_PUBLISHED = IS_STUB.replace("stub: true", "stub: true\ntranslation_status: published")

# A full (non-stub) Icelandic translation still awaiting language review.
IS_FULL_UNREVIEWED = (
    IS_STUB.replace("stub: true", "translation_status: review")
    + "\n## Athugadu fjarmaelingar {#check-telemetry}\n\nTexti.\n"
)


def _write(root, rel, text):
    path = Path(root) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md", EN)
        _write(self.tmp, "is/machines_telemetry/machine-unavailable.md", IS_STUB_PUBLISHED)
        self.settings = {"telemetry_enabled"}

    def compile(self):
        return compile_help(Path(self.tmp), "admin", self.settings, build_id="abc123")

    def test_manifest_top_level_shape(self):
        m = self.compile()
        self.assertEqual(m["schema_version"], SCHEMA_VERSION)
        self.assertEqual(m["trust_class"], "admin")
        self.assertEqual(m["build_id"], "abc123")
        self.assertEqual(m["guide_count"], 1)
        self.assertEqual(m["locales"], ["is", "en"])

    def test_translation_inherits_canonical_neutral_metadata(self):
        guide = self.compile()["guides"]["machine-unavailable"]
        self.assertEqual(guide["category"], "machines_telemetry")
        self.assertEqual(guide["risk"], "medium")
        self.assertEqual(guide["canonical_locale"], "en")

    def test_stub_has_localised_metadata_but_no_sections(self):
        locales = self.compile()["guides"]["machine-unavailable"]["locales"]
        self.assertTrue(locales["is"]["stub"])
        self.assertNotIn("sections", locales["is"])
        self.assertEqual(locales["is"]["title"], "Vélin sýnist upptekin")
        self.assertFalse(locales["en"]["stub"])
        self.assertEqual(locales["en"]["sections"][0]["anchor"], "check-telemetry")

    def test_stub_is_searchable_in_its_own_locale(self):
        record = self.compile()["search"]["machine-unavailable"]["is"]
        self.assertIn("thvottavel", record["aliases"])

    def test_output_is_deterministic(self):
        first = json.dumps(self.compile(), sort_keys=True, ensure_ascii=False)
        second = json.dumps(self.compile(), sort_keys=True, ensure_ascii=False)
        self.assertEqual(first, second)
        self.assertNotIn("generated_at", first)

    def test_unreviewed_full_translation_is_withheld(self):
        _write(self.tmp, "is/machines_telemetry/machine-unavailable.md", IS_FULL_UNREVIEWED)
        manifest = self.compile()
        self.assertNotIn("is", manifest["guides"]["machine-unavailable"]["locales"])
        self.assertEqual(
            manifest["excluded_translations"],
            [{"guide_id": "machine-unavailable", "locale": "is",
              "translation_status": "review"}],
        )

    def test_translation_without_explicit_status_defaults_to_withheld(self):
        _write(self.tmp, "is/machines_telemetry/machine-unavailable.md", IS_STUB)
        manifest = self.compile()
        self.assertNotIn("is", manifest["guides"]["machine-unavailable"]["locales"])

    def test_approved_stub_ships(self):
        locales = self.compile()["guides"]["machine-unavailable"]["locales"]
        self.assertTrue(locales["is"]["stub"])
        self.assertEqual(locales["is"]["translation_status"], "published")

    def test_canonical_locale_ships_without_declaring_translation_status(self):
        locales = self.compile()["guides"]["machine-unavailable"]["locales"]
        self.assertEqual(locales["en"]["translation_status"], "published")

    def test_canonical_status_is_unaffected_by_translation_status(self):
        _write(self.tmp, "is/machines_telemetry/machine-unavailable.md", IS_FULL_UNREVIEWED)
        guide = self.compile()["guides"]["machine-unavailable"]
        self.assertEqual(guide["status"], "published")

    def test_unknown_frontmatter_field_fails(self):
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("common_problem_rank: 1", "common_problem_rank: 1\nproblem_guide: oops"))
        with self.assertRaises(CompileError):
            self.compile()

    def test_numeric_id_fails(self):
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("id: machine-unavailable", "id: 007"))
        _write(self.tmp, "is/machines_telemetry/machine-unavailable.md",
               IS_STUB_PUBLISHED.replace("id: machine-unavailable", "id: 007"))
        with self.assertRaises(CompileError):
            self.compile()

    def test_unknown_diagnostic_group_fails(self):
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("machine.telemetry", "machine.not_a_group"))
        with self.assertRaises(CompileError):
            self.compile()

    def test_unknown_setting_key_fails(self):
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("telemetry_enabled\n---", "not_a_setting\n---"))
        with self.assertRaises(CompileError):
            self.compile()

    def test_two_canonical_locales_fails(self):
        _write(self.tmp, "is/machines_telemetry/machine-unavailable.md",
               IS_STUB_PUBLISHED.replace("stub: true", "canonical: true\nstub: true"))
        with self.assertRaises(CompileError):
            self.compile()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_compiler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.help.compiler'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/help/compiler.py
"""Compile a guide tree into one deterministic manifest.

One implementation serves both trust classes; the security boundary is the caller's
choice of root plus the snapshot test over public guide ids, never a flag inside a
guide file.
"""

from pathlib import Path

from backend.help.blocks import parse_body
from backend.help.frontmatter import split_frontmatter
from backend.help.schema import (
    CANONICAL_ONLY_FIELDS, CATEGORIES, KINDS, LOCALES, LOCALISED_OPTIONAL_FIELDS,
    REQUIRED_FIELDS, RISKS, SCHEMA_VERSION, STATUSES, TRANSLATION_STATUSES, CompileError,
)
from backend.help.search_index import build_index_record

DIAGNOSTIC_GROUPS = frozenset({
    "core", "machine.identity", "machine.telemetry", "machine.thresholds",
    "machine.mapping", "settings.telemetry", "settings.relay", "settings.scanner",
    "settings.provider", "provider.reisa", "scanner.status", "kiosk.state",
})
KNOWN_ACTIONS = frozenset({"restart_backend"})

_LIST_FIELDS = ("related_guides", "related_settings", "diagnostics", "actions", "search_aliases")


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _validate_neutral(meta, path, known_settings):
    if meta.get("category") not in CATEGORIES:
        raise CompileError(f"{path}: unknown category {meta.get('category')!r}")
    if meta.get("kind") not in KINDS:
        raise CompileError(f"{path}: unknown kind {meta.get('kind')!r}")
    if meta.get("risk") not in RISKS:
        raise CompileError(f"{path}: unknown risk {meta.get('risk')!r}")
    if meta.get("status") not in STATUSES:
        raise CompileError(f"{path}: unknown status {meta.get('status')!r}")
    for group in _as_list(meta.get("diagnostics")):
        if group not in DIAGNOSTIC_GROUPS:
            raise CompileError(f"{path}: unknown diagnostic group {group!r}")
    for action in _as_list(meta.get("actions")):
        if action not in KNOWN_ACTIONS:
            raise CompileError(f"{path}: unknown action {action!r}")
    for key in _as_list(meta.get("related_settings")):
        if key not in known_settings:
            raise CompileError(f"{path}: unknown setting key {key!r}")


def compile_help(root, trust_class, known_settings, build_id=None):
    root = Path(root)
    files = sorted(root.rglob("*.md"), key=lambda p: str(p.relative_to(root)))
    by_id, canonical = {}, {}

    for path in files:
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        missing = REQUIRED_FIELDS - set(meta)
        if missing:
            raise CompileError(f"{path}: missing required field(s) {sorted(missing)}")
        # Spec §5.2: an UNKNOWN field fails the build too. Without this, a mistyped or
        # mis-indented key (e.g. `problem_guide` escaping its check) would be silently
        # accepted and then silently ignored.
        unknown = set(meta) - REQUIRED_FIELDS - CANONICAL_ONLY_FIELDS - LOCALISED_OPTIONAL_FIELDS
        if unknown:
            raise CompileError(f"{path}: unknown field(s) {sorted(unknown)}")
        if not isinstance(meta["id"], str) or not meta["id"]:
            raise CompileError(f"{path}: id must be a non-empty string, got {meta['id']!r}")
        if meta["locale"] not in LOCALES:
            raise CompileError(f"{path}: unknown locale {meta['locale']!r}")
        guide_id, locale = meta["id"], meta["locale"]
        entry = by_id.setdefault(guide_id, {})
        if locale in entry:
            raise CompileError(f"{path}: duplicate id {guide_id!r} for locale {locale!r}")
        if meta.get("canonical"):
            if guide_id in canonical:
                raise CompileError(f"{path}: guide {guide_id!r} has more than one canonical locale")
            canonical[guide_id] = locale
            _validate_neutral(meta, path, known_settings)
        entry[locale] = (meta, body, path)

    guides, search, excluded = {}, {}, []
    for guide_id in sorted(by_id):
        locales = by_id[guide_id]
        if guide_id not in canonical:
            raise CompileError(f"guide {guide_id!r} has no canonical locale")
        canonical_locale = canonical[guide_id]
        canonical_meta = locales[canonical_locale][0]

        record = {
            "id": guide_id,
            "canonical_locale": canonical_locale,
            "category": canonical_meta["category"],
            "kind": canonical_meta["kind"],
            "risk": canonical_meta["risk"],
            "status": canonical_meta["status"],
            "last_reviewed": str(canonical_meta["last_reviewed"]),
            "related_guides": sorted(_as_list(canonical_meta.get("related_guides"))),
            "related_settings": sorted(_as_list(canonical_meta.get("related_settings"))),
            "diagnostics": sorted(_as_list(canonical_meta.get("diagnostics"))),
            "actions": sorted(_as_list(canonical_meta.get("actions"))),
            "common_problem_rank": canonical_meta.get("common_problem_rank"),
            "locales": {},
        }

        for locale in LOCALES:
            if locale not in locales:
                continue
            meta, body, path = locales[locale]
            for field in CANONICAL_ONLY_FIELDS & set(meta):
                if locale != canonical_locale and meta[field] != canonical_meta.get(field):
                    raise CompileError(
                        f"{path}: translation overrides inherited field {field!r}"
                    )
            # A translation ships only when explicitly reviewed. The canonical locale is
            # the source text, so it is always considered published; every other locale
            # must say so, which is what stops unreviewed Icelandic reaching an operator.
            translation_status = meta.get("translation_status")
            if locale == canonical_locale:
                translation_status = "published"
            elif translation_status is None:
                translation_status = "draft"
            if translation_status not in TRANSLATION_STATUSES:
                raise CompileError(
                    f"{path}: unknown translation_status {translation_status!r}"
                )
            if translation_status != "published":
                excluded.append({"guide_id": guide_id, "locale": locale,
                                 "translation_status": translation_status})
                continue

            payload = {
                "title": meta["title"],
                "summary": meta["summary"],
                "search_aliases": sorted(_as_list(meta.get("search_aliases"))),
                "stub": bool(meta.get("stub")),
                "translation_status": translation_status,
            }
            sections = []
            if not payload["stub"]:
                sections = parse_body(body, known_settings)
                payload["sections"] = sections
                if meta.get("checks"):
                    payload["checks"] = meta["checks"]
            record["locales"][locale] = payload
            search.setdefault(guide_id, {})[locale] = build_index_record(payload, sections)

        guides[guide_id] = record

    return {
        "schema_version": SCHEMA_VERSION,
        "trust_class": trust_class,
        "build_id": build_id,
        "default_locale": LOCALES[0],
        "locales": list(LOCALES),
        "guide_count": len(guides),
        "guides": guides,
        "search": search,
        # Visible rather than silent: an unreviewed translation is withheld, not lost,
        # and the list is asserted in tests so a withheld guide cannot go unnoticed.
        "excluded_translations": sorted(
            excluded, key=lambda e: (e["guide_id"], e["locale"])
        ),
    }
```

> **Corrections applied during execution (Task 5 is complete; the committed
> `backend/help/compiler.py` at `fd5ede7` is authoritative over the snippet above).** Review
> found three defects in the snippet, fixed in the shipped code:
> 1. Inherited list-field equality was order-sensitive; shipped code compares
>    `sorted(_as_list(...))` on both sides (`_normalised`), so a translation may re-list
>    `related_guides`/`related_settings`/`diagnostics`/`actions` in any order.
> 2. A canonical guide omitting `last_reviewed` raised a bare `KeyError`; shipped code validates
>    it in `_validate_neutral` and raises `CompileError`.
> 3. `checks` entries were unvalidated; shipped code (`_validate_checks`, run for EVERY locale's
>    file) requires a list of mappings each with a non-empty string `id`, so Task 6's
>    `c["id"]` can never `KeyError`.
>
> 4. (Maintainer-directed, `fd5ede7`.) List-typed fields (`related_guides`, `related_settings`,
>    `diagnostics`, `actions`, `search_aliases`) are strict: absent or a list of non-empty strings,
>    else `CompileError` — for every locale's file. `_as_list` can no longer wrap a bare scalar,
>    so an author who writes `related_settings: telemetry_enabled` gets a build error instead of
>    silent normalisation.
>
> The test file gained `test_translation_may_list_inherited_fields_in_any_order`,
> `test_missing_last_reviewed_is_a_compile_error`, `test_check_without_id_is_a_compile_error`,
> `test_scalar_in_list_field_is_a_compile_error`,
> `test_scalar_search_alias_in_translation_is_a_compile_error` (20 tests total).

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_compiler.py -v`
Expected: PASS (20 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/help/compiler.py backend/tests/test_help_compiler.py
git commit -m "feat(help): compile guide trees into deterministic manifests"
```

---

### Task 6: Cross-guide validator

**Files:**
- Create: `backend/help/validator.py`
- Test: `backend/tests/test_help_validator.py`

**Interfaces:**
- Consumes: a compiled manifest dict.
- Produces: `validate_manifest(manifest: dict) -> None`, raising `CompileError` on the first violation.

Rules: unresolvable `related_guides` / `problem_guide` / `guide_link`; duplicate anchor within a locale; anchor-set parity between non-stub translations; check-ID drift between locales; `status: published` required for every guide in a shipped manifest.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_help_validator.py
import copy
import unittest

from backend.help.schema import CompileError
from backend.help.validator import validate_manifest


def _guide(**over):
    base = {
        "id": "a", "canonical_locale": "en", "category": "machines_telemetry",
        "kind": "troubleshooting", "risk": "low", "status": "published",
        "last_reviewed": "2026-09-02", "related_guides": [], "related_settings": [],
        "diagnostics": [], "actions": [], "common_problem_rank": None,
        "locales": {
            "en": {"title": "A", "summary": "S", "search_aliases": [], "stub": False,
                   "sections": [{"anchor": "one", "heading": "One", "blocks": []}]},
        },
    }
    base.update(over)
    return base


def _manifest(guides):
    return {"schema_version": 1, "trust_class": "admin", "build_id": None,
            "default_locale": "is", "locales": ["is", "en"],
            "guide_count": len(guides), "guides": guides, "search": {}}


class ValidatorTests(unittest.TestCase):
    def test_valid_manifest_passes(self):
        validate_manifest(_manifest({"a": _guide()}))

    def test_unresolvable_related_guide_fails(self):
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": _guide(related_guides=["ghost"])}))

    def test_duplicate_anchor_fails(self):
        guide = _guide()
        guide["locales"]["en"]["sections"].append({"anchor": "one", "heading": "Dup", "blocks": []})
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": guide}))

    def test_anchor_parity_between_full_translations_enforced(self):
        guide = _guide()
        guide["locales"]["is"] = {
            "title": "A", "summary": "S", "search_aliases": [], "stub": False,
            "sections": [{"anchor": "different", "heading": "Annad", "blocks": []}],
        }
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": guide}))

    def test_stub_is_exempt_from_anchor_parity(self):
        guide = _guide()
        guide["locales"]["is"] = {"title": "A", "summary": "S", "search_aliases": [], "stub": True}
        validate_manifest(_manifest({"a": guide}))

    def test_check_id_drift_between_locales_fails(self):
        guide = _guide()
        guide["locales"]["en"]["checks"] = [{"id": "c1", "question": "q"}]
        guide["locales"]["is"] = copy.deepcopy(guide["locales"]["en"])
        guide["locales"]["is"]["checks"] = [{"id": "c2", "question": "s"}]
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": guide}))

    def test_unpublished_guide_fails(self):
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": _guide(status="draft")}))

    def test_broken_guide_link_in_body_fails(self):
        guide = _guide()
        guide["locales"]["en"]["sections"][0]["blocks"] = [
            {"type": "paragraph", "inlines": [{"type": "guide_link", "guide_id": "ghost", "text": "x"}]}
        ]
        with self.assertRaises(CompileError):
            validate_manifest(_manifest({"a": guide}))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_validator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.help.validator'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/help/validator.py
"""Cross-guide rules. Every violation fails the build.

A broken cross-reference is worse here than in ordinary docs: an operator hits it
mid-incident, so it must never reach a manifest.
"""

from backend.help.schema import CompileError


def _walk_inlines(inlines, sink):
    for inline in inlines or []:
        if inline.get("type") == "guide_link":
            sink.append(inline["guide_id"])
        _walk_inlines(inline.get("inlines"), sink)


def _walk_blocks(blocks, sink):
    for block in blocks or []:
        _walk_inlines(block.get("inlines"), sink)
        _walk_blocks(block.get("blocks"), sink)
        for item in block.get("items", []) or []:
            _walk_blocks(item, sink)
        for row in [block.get("header", [])] + (block.get("rows") or []):
            for cell in row or []:
                _walk_inlines(cell, sink)


def validate_manifest(manifest):
    guides = manifest["guides"]
    known = set(guides)

    for guide_id, guide in sorted(guides.items()):
        if guide.get("status") != "published":
            raise CompileError(f"{guide_id}: status must be 'published' to ship, got "
                               f"{guide.get('status')!r}")
        for ref in guide.get("related_guides", []):
            if ref not in known:
                raise CompileError(f"{guide_id}: related_guides references unknown {ref!r}")

        anchor_sets, check_id_sets = {}, {}
        for locale, payload in sorted(guide["locales"].items()):
            if payload.get("stub"):
                continue
            anchors = [s["anchor"] for s in payload.get("sections", []) if s.get("anchor")]
            if len(anchors) != len(set(anchors)):
                raise CompileError(f"{guide_id} [{locale}]: duplicate section anchor")
            anchor_sets[locale] = set(anchors)

            refs = []
            for section in payload.get("sections", []):
                _walk_blocks(section.get("blocks"), refs)
            for ref in refs:
                if ref not in known:
                    raise CompileError(f"{guide_id} [{locale}]: guide_link to unknown {ref!r}")

            checks = payload.get("checks") or []
            check_id_sets[locale] = [c["id"] for c in checks]
            for check in checks:
                target = check.get("problem_guide")
                if target and target not in known:
                    raise CompileError(
                        f"{guide_id} [{locale}]: check {check['id']!r} problem_guide "
                        f"references unknown {target!r}"
                    )

        distinct_anchors = {frozenset(v) for v in anchor_sets.values()}
        if len(distinct_anchors) > 1:
            raise CompileError(f"{guide_id}: section anchors differ between full translations")
        distinct_checks = {tuple(v) for v in check_id_sets.values()}
        if len(distinct_checks) > 1:
            raise CompileError(f"{guide_id}: check ids differ between full translations")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_validator.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/help/validator.py backend/tests/test_help_validator.py
git commit -m "feat(help): validate cross-guide references, anchors and checks"
```

---

### Task 7: Compiler CLI and committed artifacts

**Files:**
- Create: `backend/help/cli.py`, `backend/help/generated/.gitkeep`, `frontend/src/generated/.gitkeep`
- Create (content seed): `docs/admin-guides/en/daily_operation/admin-panel-orientation.md`, `docs/public-help/backend-unavailable.md`
- Test: `backend/tests/test_help_artifacts.py`

**Interfaces:**
- Consumes: `compile_help`, `validate_manifest`.
- Produces: `python -m backend.help.cli [--check]`; `ADMIN_ROOT`, `PUBLIC_ROOT`, `ADMIN_ARTIFACT`, `PUBLIC_ARTIFACT`, `write_artifacts() -> None`, `git_build_id() -> str | None`.

`--check` recompiles and exits non-zero on any drift. The staleness test calls the same code path, so a forgotten recompile fails CI and local `pytest` alike.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_help_artifacts.py
import json
import unittest

from backend.help import cli


class ArtifactTests(unittest.TestCase):
    def test_committed_admin_manifest_is_current(self):
        fresh = cli.build_manifest(cli.ADMIN_ROOT, "admin")
        committed = json.loads(cli.ADMIN_ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(cli.serialise(fresh), cli.ADMIN_ARTIFACT.read_text(encoding="utf-8"),
                         msg="admin manifest is stale; run: python -m backend.help.cli")
        self.assertEqual(committed["trust_class"], "admin")

    def test_committed_public_manifest_is_current(self):
        fresh = cli.build_manifest(cli.PUBLIC_ROOT, "public_bootstrap")
        self.assertEqual(cli.serialise(fresh), cli.PUBLIC_ARTIFACT.read_text(encoding="utf-8"),
                         msg="public manifest is stale; run: python -m backend.help.cli")

    def test_public_manifest_guide_ids_are_snapshotted(self):
        committed = json.loads(cli.PUBLIC_ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(committed["guides"]),
            ["backend-unavailable"],
            msg="public help content changed: this list is a deliberate security review gate",
        )

    def test_admin_manifest_may_reference_secret_setting_identifiers(self):
        """`api_key` is a setting NAME, not a credential.

        An admin guide about credential rotation has to be able to say the word. The
        test that matters is that no credential VALUE is present, not that the
        identifier is banned -- banning it would make legitimate documentation
        impossible. Prove the identifier is permitted by compiling a guide that uses it.
        """
        import tempfile
        from pathlib import Path
        from backend.help.compiler import compile_help

        root = Path(tempfile.mkdtemp())
        guide = root / "en" / "admin_recovery" / "rotate-credentials.md"
        guide.parent.mkdir(parents=True)
        guide.write_text(
            "---\nid: rotate-credentials\nlocale: en\ncanonical: true\n"
            "title: Rotate credentials\nsummary: How to rotate the API key.\n"
            "category: admin_recovery\nkind: procedure\nrisk: high\nstatus: published\n"
            "last_reviewed: 2026-09-02\nrelated_settings:\n  - api_key\n---\n\n"
            "## Steps {#steps}\n\nRotate `api_key` from the Security panel.\n",
            encoding="utf-8",
        )
        manifest = compile_help(root, "admin", cli.known_setting_keys(), build_id=None)
        self.assertEqual(manifest["guides"]["rotate-credentials"]["related_settings"], ["api_key"])

    def test_admin_manifest_contains_no_credential_shaped_values(self):
        import re
        text = cli.ADMIN_ARTIFACT.read_text(encoding="utf-8")
        # 32+ hex chars covers api_key (64 hex) and sha256 password hashes;
        # 40+ base64-ish chars covers bearer tokens.
        for pattern in (r"[A-Fa-f0-9]{32,}", r"[A-Za-z0-9+/]{40,}={0,2}"):
            hits = re.findall(pattern, text)
            self.assertEqual(hits, [], msg=f"credential-shaped value in admin manifest: {hits[:1]}")

    def test_public_manifest_rejects_privileged_identifiers_entirely(self):
        """The public tier is stricter on purpose: it is readable by anyone on the LAN,
        so even naming a privileged setting or procedure is out of bounds."""
        text = cli.PUBLIC_ARTIFACT.read_text(encoding="utf-8").lower()
        for forbidden in ("api_key", "admin_password_hash", "reisa_bearer_token",
                          "dev_admin_enabled", "backend_relay_enabled",
                          "update_setting_value", ".venv/bin/activate", "sqlite3"):
            self.assertNotIn(forbidden, text,
                             msg=f"{forbidden!r} must never reach the public tier")

    def test_build_id_is_the_only_volatile_field(self):
        text = cli.ADMIN_ARTIFACT.read_text(encoding="utf-8")
        self.assertNotIn("generated_at", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_artifacts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.help.cli'`

- [ ] **Step 3: Write minimal implementation**

Author the two seed guides first (full content in Task 16; a minimal published guide is enough to make the artifacts real here), then:

```python
# backend/help/cli.py
"""Compile both Help manifests.

Run after editing any guide:   python -m backend.help.cli
Verify without writing:        python -m backend.help.cli --check
"""

import json
import subprocess
import sys
from pathlib import Path

from backend.help.compiler import compile_help
from backend.help.validator import validate_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADMIN_ROOT = REPO_ROOT / "docs" / "admin-guides"
PUBLIC_ROOT = REPO_ROOT / "docs" / "public-help"
ADMIN_ARTIFACT = REPO_ROOT / "backend" / "help" / "generated" / "admin-help-manifest.json"
PUBLIC_ARTIFACT = REPO_ROOT / "frontend" / "src" / "generated" / "public-help-manifest.json"


def git_build_id():
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


def known_setting_keys():
    from backend.services.dev_admin_service import SETTING_SCHEMA
    return set(SETTING_SCHEMA)


def build_manifest(root, trust_class):
    manifest = compile_help(root, trust_class, known_setting_keys(), build_id=None)
    validate_manifest(manifest)
    return manifest


def serialise(manifest):
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_artifacts():
    for root, trust_class, artifact in (
        (ADMIN_ROOT, "admin", ADMIN_ARTIFACT),
        (PUBLIC_ROOT, "public_bootstrap", PUBLIC_ARTIFACT),
    ):
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(serialise(build_manifest(root, trust_class)), encoding="utf-8")
        print(f"wrote {artifact.relative_to(REPO_ROOT)}")


def main(argv):
    check_only = "--check" in argv
    drift = False
    for root, trust_class, artifact in (
        (ADMIN_ROOT, "admin", ADMIN_ARTIFACT),
        (PUBLIC_ROOT, "public_bootstrap", PUBLIC_ARTIFACT),
    ):
        fresh = serialise(build_manifest(root, trust_class))
        if check_only:
            current = artifact.read_text(encoding="utf-8") if artifact.exists() else ""
            if fresh != current:
                print(f"STALE: {artifact.relative_to(REPO_ROOT)}", file=sys.stderr)
                drift = True
        else:
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(fresh, encoding="utf-8")
            print(f"wrote {artifact.relative_to(REPO_ROOT)}")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

`build_id` is deliberately `None` inside the committed artifact so the file stays stable across commits; the live value is attached at serve time in Task 8.

- [ ] **Step 4: Generate the artifacts, then run the test**

Run: `source .venv/bin/activate && python -m backend.help.cli && python -m pytest backend/tests/test_help_artifacts.py -v`
Expected: two `wrote …` lines, then PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/help/cli.py backend/help/generated/ frontend/src/generated/ \
        docs/admin-guides/ docs/public-help/ backend/tests/test_help_artifacts.py
git commit -m "feat(help): add compiler CLI and committed manifest artifacts"
```

---

### Task 8: Failure-isolated manifest loader

**Files:**
- Create: `backend/services/help_service.py`
- Test: `backend/tests/test_help_service.py`

**Interfaces:**
- Consumes: `cli.ADMIN_ARTIFACT`, `cli.git_build_id`, `schema.SCHEMA_VERSION`.
- Produces: `get_manifest() -> dict | None`, `get_status() -> dict`, `get_guide(guide_id) -> dict | None`, `get_provenance() -> dict`, `reset_cache() -> None`, `SCHEMA_VERSION`.

`get_provenance()` returns `{"schema_version", "manifest_digest", "build_id"}`. The digest is
the first 12 hex characters of the SHA-256 of the artifact bytes, **computed at load time and
never written into the artifact** — so support reports can name the exact knowledge version
while the committed manifest stays byte-deterministic.

This is the task that guarantees **Help can fail but the backend cannot fail because Help failed**. Nothing here may raise to the caller.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_help_service.py
import json
import unittest
from unittest.mock import patch

from backend.services import help_service


class HelpServiceTests(unittest.TestCase):
    def setUp(self):
        help_service.reset_cache()

    def tearDown(self):
        help_service.reset_cache()

    def test_loads_the_committed_manifest(self):
        self.assertIsNotNone(help_service.get_manifest())
        status = help_service.get_status()
        self.assertTrue(status["available"])
        self.assertEqual(status["schema_version"], help_service.SCHEMA_VERSION)
        self.assertGreater(status["guide_count"], 0)

    def test_missing_artifact_degrades_without_raising(self):
        with patch.object(help_service, "_read_artifact", side_effect=FileNotFoundError("gone")):
            self.assertIsNone(help_service.get_manifest())
            status = help_service.get_status()
        self.assertFalse(status["available"])
        self.assertEqual(status["reason"], "manifest_missing")

    def test_malformed_json_degrades_without_raising(self):
        with patch.object(help_service, "_read_artifact", return_value="{not json"):
            self.assertIsNone(help_service.get_manifest())
            self.assertEqual(help_service.get_status()["reason"], "manifest_unreadable")

    def test_incompatible_schema_version_degrades(self):
        payload = json.dumps({"schema_version": 999, "guides": {}, "guide_count": 0})
        with patch.object(help_service, "_read_artifact", return_value=payload):
            self.assertIsNone(help_service.get_manifest())
            self.assertEqual(help_service.get_status()["reason"], "schema_version_unsupported")

    def test_get_guide_is_a_dict_lookup_and_never_touches_the_filesystem(self):
        self.assertIsNone(help_service.get_guide("../../etc/passwd"))
        self.assertIsNone(help_service.get_guide("does-not-exist"))

    def test_provenance_is_available_and_deterministic(self):
        first = help_service.get_provenance()
        self.assertEqual(first["schema_version"], help_service.SCHEMA_VERSION)
        self.assertRegex(first["manifest_digest"], r"^[0-9a-f]{12}$")
        self.assertEqual(first, help_service.get_provenance())

    def test_provenance_survives_a_broken_manifest(self):
        with patch.object(help_service, "_read_artifact", side_effect=OSError("io")):
            help_service.reset_cache()
            self.assertIsNone(help_service.get_provenance()["manifest_digest"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'help_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/services/help_service.py
"""Load the compiled Help manifest once, behind a failure boundary.

Help is a support feature; the kiosk is the product. A missing, malformed, or
version-incompatible manifest must degrade Help alone -- it must never raise into
backend import, the telemetry loop, scanning, or machine control.
"""

import hashlib
import json
import logging

from backend.help.cli import ADMIN_ARTIFACT, git_build_id
from backend.help.schema import SCHEMA_VERSION

logger = logging.getLogger(__name__)

_cache = None          # None = not yet attempted
_status = None
_digest = None


def _read_artifact():
    return ADMIN_ARTIFACT.read_text(encoding="utf-8")


def _load():
    global _cache, _status, _digest
    try:
        raw = _read_artifact()
        _digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        payload = json.loads(raw)
    except FileNotFoundError:
        _cache, _status = None, {"available": False, "reason": "manifest_missing"}
        logger.error("Help manifest missing at %s; Help disabled, backend unaffected", ADMIN_ARTIFACT)
        return
    except (OSError, ValueError) as exc:
        _cache, _status = None, {"available": False, "reason": "manifest_unreadable"}
        logger.error("Help manifest unreadable (%s); Help disabled, backend unaffected", exc)
        return
    except Exception as exc:  # pragma: no cover - defensive, must never escape
        _cache, _status = None, {"available": False, "reason": "manifest_unreadable"}
        logger.exception("Unexpected Help manifest failure (%s); Help disabled", exc)
        return

    if payload.get("schema_version") != SCHEMA_VERSION:
        _cache, _status = None, {
            "available": False,
            "reason": "schema_version_unsupported",
            "found_schema_version": payload.get("schema_version"),
        }
        logger.error("Help manifest schema %s != supported %s; Help disabled",
                     payload.get("schema_version"), SCHEMA_VERSION)
        return

    _cache = payload
    _status = {
        "available": True,
        "schema_version": payload["schema_version"],
        "guide_count": payload.get("guide_count", 0),
        "locales": payload.get("locales", []),
        "default_locale": payload.get("default_locale"),
        "build_id": git_build_id(),
    }


def _ensure():
    if _status is None:
        _load()


def reset_cache():
    global _cache, _status, _digest
    _cache, _status, _digest = None, None, None


def get_manifest():
    _ensure()
    return _cache


def get_status():
    _ensure()
    return dict(_status)


def get_guide(guide_id):
    manifest = get_manifest()
    if not manifest:
        return None
    return manifest.get("guides", {}).get(guide_id)


def get_provenance():
    """Which knowledge version a support report or AI citation was built from."""
    _ensure()
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_digest": _digest,
        "build_id": git_build_id(),
    }
```

> **Corrections applied during execution (Task 8 is complete; the committed
> `backend/services/help_service.py` at `3c5ea99` is authoritative over the snippet above).**
> The snippet's `_load()` let two exception paths escape the failure boundary — the exact
> property this task exists to guarantee. Both are closed at the load boundary, so every
> accessor is safe by construction:
> 1. `payload.get("schema_version")` ran outside the `try/except`; a valid-JSON non-object
>    artifact (`[]`, `42`, `null`) raised `AttributeError`. Shipped code checks
>    `isinstance(payload, dict)` first and reports `manifest_unreadable` (found by the
>    implementer, who correctly stopped before committing).
> 2. A dict manifest with a matching `schema_version` but a non-dict `"guides"` was cached, and
>    `get_guide()` then raised. Shipped code checks `isinstance(guides, dict)` in `_load()`
>    after the schema check and reports `manifest_unreadable`; `get_guide()` is unchanged.
>
> Both are pinned by subtests (`test_non_object_json_degrades_without_raising`,
> `test_malformed_guides_field_degrades_without_raising`); 9 test methods / 8 subtests.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_service.py -v && python -m pytest backend/tests/ -q`
Expected: PASS (9 test methods / 8 subtests), then the whole suite green

- [ ] **Step 5: Commit**

```bash
git add backend/services/help_service.py backend/tests/test_help_service.py
git commit -m "feat(help): load the manifest behind a failure-isolated boundary"
```

---

### Task 9: Support projection service

**Files:**
- Create: `backend/services/support_service.py`
- Test: `backend/tests/test_support_service.py`

**Interfaces:**
- Consumes: `help_service.get_guide`, `help_service.get_provenance`, `telemetry.MachineStateStore`, `machine_control.UI_STATE`, `setting_model.get_setting_value`, `dev_admin_service.SECRET_KEYS`, `dev_admin_service.scanner_status`.
- Produces: `build_support_report(db, guide_id=None, machine_id=None, checks=None, locale="is", locale_shown=None, groups=None) -> dict`; `GROUP_HANDLERS: dict[str, callable]`; `CORE_GROUPS: tuple[str, ...]`; `SAFE_SETTING_KEYS: tuple[str, ...]`; `SECTION_ORDER: tuple[str, ...]`; `MACHINE_SUBSECTION_ORDER: tuple[str, ...]`; `render_report_text(report, locale) -> str`.

**The client never names a group.** Groups come from the guide's compiled `diagnostics` list,
intersected with the server allowlist.

**Machine groups compose by machine id, not by overwrite.** Four groups
(`machine.identity`, `machine.telemetry`, `machine.thresholds`, `machine.mapping`) all describe
the same machines. A flat `data["machine"].update(...)` would let each group destroy the
previous one, so machine data is keyed `data["machines"][<machine_id>][<subsection>]`. That
also gives a future AI a deterministic citation path such as
`data.machines.washer1.telemetry.last_value`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_support_service.py
import re
import unittest

from backend.models import Session, init_db
from backend.models.setting_model import update_setting_value
from backend.services import support_service
from backend.services.dev_admin_service import SECRET_KEYS


class SupportReportTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = Session()
        update_setting_value(self.db, "api_key", "super-secret-key")
        update_setting_value(self.db, "reisa_bearer_token", "super-secret-token")
        update_setting_value(self.db, "telemetry_enabled", "true")

    def tearDown(self):
        self.db.close()

    def test_core_report_needs_no_guide(self):
        report = support_service.build_support_report(self.db)
        self.assertIn("generated_at", report)
        self.assertIn("kiosk", report["data"])
        self.assertIsNone(report["guide_id"])

    def test_secret_values_never_appear_anywhere(self):
        blob = repr(support_service.build_support_report(self.db))
        self.assertNotIn("super-secret-key", blob)
        self.assertNotIn("super-secret-token", blob)

    def test_secrets_are_presence_only(self):
        report = support_service.build_support_report(self.db)
        self.assertIs(report["data"]["provider"]["reisa_token_configured"], True)

    def test_every_secret_key_is_excluded_from_the_safe_allowlist(self):
        for key in SECRET_KEYS:
            self.assertNotIn(key, support_service.SAFE_SETTING_KEYS)

    def test_all_four_machine_groups_compose_without_loss(self):
        """The bug this guards: four groups describing the same machines used to be
        merged with dict.update(), so only the last group survived."""
        from backend.controllers.telemetry import MachineStateStore

        report = support_service.build_support_report(
            self.db,
            groups=(
                "machine.identity", "machine.telemetry",
                "machine.thresholds", "machine.mapping",
            ),
        )
        machines = report["data"]["machines"]
        if not MachineStateStore.instance().get_diagnostic_snapshot():
            self.assertEqual(machines, {})
            return
        for machine_id, sections in machines.items():
            self.assertEqual(
                sorted(sections),
                ["identity", "mapping", "telemetry", "thresholds"],
                msg=f"machine {machine_id} lost a diagnostic group",
            )

    def test_machine_sections_carry_their_own_fields(self):
        from backend.controllers.telemetry import MachineStateStore
        if not MachineStateStore.instance().get_diagnostic_snapshot():
            self.skipTest("no machines loaded in the telemetry runtime")
        report = support_service.build_support_report(
            self.db, groups=("machine.identity", "machine.telemetry")
        )
        sections = next(iter(report["data"]["machines"].values()))
        self.assertIn("run_state", sections["identity"])
        self.assertIn("last_value", sections["telemetry"])

    def test_report_carries_knowledge_provenance(self):
        report = support_service.build_support_report(self.db)
        self.assertIn("help", report)
        self.assertIn("schema_version", report["help"])
        self.assertIn("manifest_digest", report["help"])
        self.assertIn("build_id", report["help"])

    def test_locale_fields_are_recorded_for_translation_backlog(self):
        report = support_service.build_support_report(
            self.db, locale="is", locale_shown="en"
        )
        self.assertEqual(report["locale_requested"], "is")
        self.assertEqual(report["locale_shown"], "en")

    def test_unknown_guide_id_falls_back_to_core_groups(self):
        report = support_service.build_support_report(self.db, guide_id="../../etc/passwd")
        self.assertIsNone(report["guide_id"])
        self.assertIn("kiosk", report["data"])

    def test_checklist_evidence_is_carried_through(self):
        report = support_service.build_support_report(
            self.db, checks=[{"check_id": "telemetry-enabled", "result": "problem"}]
        )
        self.assertEqual(report["checks"][0]["result"], "problem")

    def test_invalid_check_result_is_dropped(self):
        report = support_service.build_support_report(
            self.db, checks=[{"check_id": "c", "result": "banana"}]
        )
        self.assertEqual(report["checks"], [])

    # ----- machine scoping -----

    def test_unknown_or_malformed_machine_id_narrows_to_nothing(self):
        """A bad machine_id must never widen the report to every machine."""
        groups = ("machine.identity", "machine.telemetry")
        for bad in ("no-such-machine", "", "   ", {}, [], 0, 7):
            with self.subTest(machine_id=bad):
                report = support_service.build_support_report(self.db, machine_id=bad, groups=groups)
                self.assertEqual(report["data"].get("machines", {}), {})

    def test_none_machine_id_means_unscoped(self):
        report = support_service.build_support_report(
            self.db, machine_id=None, groups=("machine.identity",)
        )
        from backend.controllers.telemetry import MachineStateStore
        expected = {r["id"] for r in MachineStateStore.instance().get_diagnostic_snapshot()}
        self.assertEqual(set(report["data"].get("machines", {})), expected)

    # ----- authorisation boundary -----

    def test_core_report_never_includes_mapping(self):
        report = support_service.build_support_report(self.db)
        for sections in report["data"].get("machines", {}).values():
            self.assertNotIn("mapping", sections)
        self.assertNotIn("machine.mapping", report["groups"])

    def test_unknown_group_names_are_ignored_even_in_process(self):
        report = support_service.build_support_report(
            self.db, groups=("secrets.everything", "machine.telemetry", "../etc")
        )
        self.assertNotIn("secrets.everything", report["groups"])
        self.assertNotIn("../etc", report["groups"])
        self.assertIn("machine.telemetry", report["groups"])

    # ----- partial failure -----

    def test_one_failing_group_yields_a_safe_marker_and_a_complete_report(self):
        from unittest.mock import patch

        def boom(db, machine_id, data):
            raise RuntimeError("Bearer super-secret-token /home/pi/internal/path")

        with patch.dict(support_service.GROUP_HANDLERS, {"scanner.status": boom}):
            report = support_service.build_support_report(self.db)
        self.assertEqual(report["data"]["errors"]["scanner.status"], "unavailable")
        self.assertIn("kiosk", report["data"])          # other groups still gathered
        self.assertIn("provider", report["data"])
        blob = repr(report)
        self.assertNotIn("super-secret-token", blob)
        self.assertNotIn("/home/pi", blob)
        self.assertNotIn("RuntimeError", blob)

    # ----- provenance -----

    def test_provenance_digest_is_the_loaded_manifest_digest(self):
        import hashlib
        from backend.help.cli import ADMIN_ARTIFACT
        from backend.services import help_service

        help_service.reset_cache()
        report = support_service.build_support_report(self.db)
        expected = hashlib.sha256(ADMIN_ARTIFACT.read_bytes()).hexdigest()[:12]
        self.assertEqual(report["help"]["manifest_digest"], expected)
        self.assertEqual(report["help"], help_service.get_provenance())

    # ----- no side effects -----

    def test_building_a_report_is_strictly_read_only(self):
        from unittest.mock import patch
        from backend.models.setting_model import Settings

        before = sorted((s.key, s.value) for s in self.db.query(Settings).all())
        with patch("backend.utils.shelly_control.send_shelly_pulse") as pulse, \
             patch("backend.utils.shelly_control.shelly_switch_on") as on, \
             patch("backend.utils.shelly_control.shelly_switch_off") as off, \
             patch("requests.get") as http_get, patch("requests.post") as http_post:
            support_service.build_support_report(
                self.db, groups=("machine.identity", "machine.telemetry",
                                 "machine.thresholds", "machine.mapping",
                                 "settings.relay", "settings.scanner"),
            )
        after = sorted((s.key, s.value) for s in self.db.query(Settings).all())
        self.assertEqual(before, after)
        for mock in (pulse, on, off, http_get, http_post):
            mock.assert_not_called()

    # ----- unknown future sections -----

    def test_unknown_future_sections_render_after_known_ones_deterministically(self):
        report = {
            "generated_at": "t", "guide_id": None, "locale_requested": "en", "locale_shown": "en",
            "help": {"schema_version": 1, "manifest_digest": "abc", "build_id": None},
            "checks": [],
            "data": {"zzz_future": {"k": 1}, "kiosk": {"state": "x"}, "aaa_future": {"k": 2},
                     "app": {"name": "Vending-Washer"}},
        }
        text = support_service.render_report_text(report, "en")
        headings = [l for l in text.splitlines() if l.startswith("## ")]
        self.assertEqual(headings, ["## app", "## kiosk", "## aaa_future", "## zzz_future"])

    def test_rendered_sections_follow_diagnostic_importance_order(self):
        """Pins the human-readable order so it cannot quietly revert to alphabetical.

        The structured report is deterministic on its own; this protects the text a
        developer actually reads when a report is pasted into a chat.
        """
        report = {
            "generated_at": "2026-09-02T00:00:00Z", "guide_id": "g",
            "locale_requested": "is", "locale_shown": "is",
            "help": {"schema_version": 1, "manifest_digest": "abcdef012345", "build_id": None},
            "checks": [{"check_id": "c", "result": "ok"}],
            # Deliberately alphabetical-hostile insertion order.
            "data": {
                "settings": {"telemetry_enabled": "true"},
                "scanner": {"serial_available": False},
                "provider": {"reisa_enabled": False},
                "machines": {"washer1": {
                    "mapping": {"device": {}},
                    "thresholds": {"config": {}},
                    "telemetry": {"last_value": 1},
                    "identity": {"name": "Washer 1"},
                }},
                "kiosk": {"state": "waiting_for_code"},
                "app": {"name": "Vending-Washer"},
            },
        }
        text = support_service.render_report_text(report, "en")
        headings = [line for line in text.splitlines() if line.startswith("## ")]
        self.assertEqual(
            headings,
            ["## app", "## kiosk", "## Machines", "## provider", "## scanner",
             "## settings", "## Checks"],
        )
        machine_lines = [line for line in text.splitlines() if line.startswith("- ")
                         and "." in line.split(":")[0]]
        subsections = [line[2:].split(".")[0] for line in machine_lines]
        self.assertEqual(subsections, ["identity", "telemetry", "thresholds", "mapping"])
        # Provenance must appear before any diagnostic section.
        self.assertLess(text.index("help_manifest_digest"), text.index("## app"))

    def test_rendered_text_is_readable_and_secret_free(self):
        report = support_service.build_support_report(self.db)
        text = support_service.render_report_text(report, "is")
        self.assertIn("Vending-Washer", text)
        self.assertNotIn("super-secret-key", text)
        self.assertRegex(text, r"help_manifest_digest: [0-9a-f]{12}")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_support_service.py -v`
Expected: FAIL — `ImportError: cannot import name 'support_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/services/support_service.py
"""Allowlisted, read-only runtime projection for escalation reports.

One mechanism serves the support report today and system-aware guide cards and AI
context later. Guides name diagnostic groups; this module decides what a group means
and which fields are safe. The client never names a group or a field.
"""

import logging
from datetime import datetime

from backend.help.schema import CHECK_RESULTS
from backend.models.setting_model import get_setting_value, parse_setting_bool
from backend.services.dev_admin_service import SECRET_KEYS, scanner_status
from backend.services.help_service import get_guide, get_provenance

logger = logging.getLogger(__name__)

CORE_GROUPS = ("core", "kiosk.state", "settings.provider", "scanner.status")

SAFE_SETTING_KEYS = (
    "telemetry_enabled", "backend_relay_enabled", "button_box_enabled",
    "kiosk_input_mode", "provider_default", "provider_reisa_enabled",
    "machine_reservation_minutes", "relay_pulse_duration_sec",
    "shelly_http_timeout_sec", "telemetry_http_timeout_sec",
    "scan_timeout", "serial_port", "serial_baudrate",
)
assert not (set(SAFE_SETTING_KEYS) & SECRET_KEYS), "secret key leaked into the safe allowlist"

# Field names taken verbatim from MachineStateStore.get_diagnostic_snapshot().
_MACHINE_SECTIONS = {
    "machine.identity": ("identity", ("name", "is_enabled", "available", "run_state", "pending_start")),
    "machine.telemetry": ("telemetry", ("last_value", "band", "seconds_since_read",
                                        "seconds_above", "seconds_below")),
    "machine.thresholds": ("thresholds", ("config",)),
    "machine.mapping": ("mapping", ("device",)),
}


def _snapshot(machine_id):
    """Rows for the report's machine scope.

    Only ``None`` means "all machines". Any other value must be a non-empty string
    matching a machine id; a falsy or non-string value (``""``, ``{}``, ``0`` from a
    malformed request body) narrows to NOTHING rather than accidentally widening to
    every machine.
    """
    from backend.controllers.telemetry import MachineStateStore
    rows = MachineStateStore.instance().get_diagnostic_snapshot()
    if machine_id is None:
        return rows
    if not isinstance(machine_id, str) or not machine_id.strip():
        return []
    return [r for r in rows if r.get("id") == machine_id.strip()]


def _machine_group(group):
    subsection, fields = _MACHINE_SECTIONS[group]

    def handler(db, machine_id, data):
        machines = data.setdefault("machines", {})
        for row in _snapshot(machine_id):
            entry = machines.setdefault(row["id"], {})
            entry[subsection] = {f: row.get(f) for f in fields if f in row}

    return handler


def _core(db, machine_id, data):
    data.setdefault("app", {})["name"] = "Vending-Washer"


def _kiosk(db, machine_id, data):
    from backend.controllers.machine_control import UI_STATE
    data.setdefault("kiosk", {}).update({
        "state": UI_STATE.get("state"),
        "current_machine": UI_STATE.get("current_machine"),
    })


def _provider(db, machine_id, data):
    data.setdefault("provider", {}).update({
        "provider_default": get_setting_value(db, "provider_default"),
        "reisa_enabled": parse_setting_bool(
            get_setting_value(db, "provider_reisa_enabled"), default=False),
        "reisa_base_url_configured": bool(get_setting_value(db, "reisa_base_url")),
        "reisa_token_configured": bool(get_setting_value(db, "reisa_bearer_token")),
    })


def _scanner(db, machine_id, data):
    data.setdefault("scanner", {}).update(scanner_status(db))


def _settings_group(keys):
    def handler(db, machine_id, data):
        section = data.setdefault("settings", {})
        for key in keys:
            section[key] = get_setting_value(db, key)
    return handler


GROUP_HANDLERS = {
    "core": _core,
    "kiosk.state": _kiosk,
    "settings.provider": _provider,
    "provider.reisa": _provider,
    "scanner.status": _scanner,
    "machine.identity": _machine_group("machine.identity"),
    "machine.telemetry": _machine_group("machine.telemetry"),
    "machine.thresholds": _machine_group("machine.thresholds"),
    "machine.mapping": _machine_group("machine.mapping"),
    "settings.telemetry": _settings_group(("telemetry_enabled", "telemetry_http_timeout_sec")),
    "settings.relay": _settings_group(("backend_relay_enabled", "relay_pulse_duration_sec",
                                       "shelly_http_timeout_sec")),
    "settings.scanner": _settings_group(("scan_timeout", "serial_port", "serial_baudrate")),
}


def _resolve_groups(guide_id, groups):
    """Groups come from the guide, or from a caller inside this process.

    `groups` is not reachable from the HTTP layer: the route passes only `guide_id`.
    It exists so tests and future in-process consumers can request a projection
    directly without inventing a fake guide.
    """
    guide = get_guide(guide_id) if guide_id else None
    resolved = list(CORE_GROUPS)
    declared = list(groups) if groups else (guide.get("diagnostics", []) if guide else [])
    for group in declared:
        if group in GROUP_HANDLERS and group not in resolved:
            resolved.append(group)
    return guide, resolved


def _clean_checks(checks):
    cleaned = []
    for check in checks or []:
        if not isinstance(check, dict):
            continue
        check_id, result = check.get("check_id"), check.get("result")
        if result in CHECK_RESULTS and isinstance(check_id, str) and check_id:
            cleaned.append({"check_id": check_id, "result": result})
    return cleaned


def build_support_report(db, guide_id=None, machine_id=None, checks=None,
                         locale="is", locale_shown=None, groups=None):
    guide, resolved = _resolve_groups(guide_id, groups)
    data = {}
    for group in resolved:
        try:
            GROUP_HANDLERS[group](db, machine_id, data)
        except Exception:  # one broken group must not sink the whole report
            # A fixed marker only: never the exception text, which could carry
            # internal paths or values the allowlist exists to keep out.
            data.setdefault("errors", {})[group] = "unavailable"
            logger.warning("support report: diagnostic group %s unavailable", group)

    return {
        "schema_version": 1,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "help": get_provenance(),
        "guide_id": guide["id"] if guide else None,
        "locale_requested": locale,
        "locale_shown": locale_shown or locale,
        "groups": resolved,
        "machine_id": machine_id,
        "checks": _clean_checks(checks),
        "data": data,
    }


_LABELS = {
    "is": {"title": "Stuðningsskýrsla", "checks": "Athuganir", "machines": "Vélar",
           "errors": "Villur við söfnun"},
    "en": {"title": "Support report", "checks": "Checks", "machines": "Machines",
           "errors": "Collection errors"},
}

# Human-readable order is by diagnostic importance, so a developer can read the top
# of a pasted report and understand the incident before scrolling. The structured
# JSON stays deterministic on its own; this order applies only to the rendered text.
SECTION_ORDER = ("app", "kiosk", "machines", "provider", "scanner", "settings", "errors")
MACHINE_SUBSECTION_ORDER = ("identity", "telemetry", "thresholds", "mapping")


def _ordered(keys, order):
    """Known keys in importance order, then anything unexpected alphabetically."""
    known = [k for k in order if k in keys]
    return known + sorted(k for k in keys if k not in order)


def render_report_text(report, locale="is"):
    labels = _LABELS.get(locale, _LABELS["en"])
    help_meta = report.get("help", {})
    data = report.get("data", {})
    lines = [
        f"# {labels['title']} — Vending-Washer",
        f"generated_at: {report['generated_at']}",
        f"guide_id: {report['guide_id']}",
        f"locale_requested: {report['locale_requested']}  locale_shown: {report['locale_shown']}",
        f"help_schema_version: {help_meta.get('schema_version')}",
        f"help_manifest_digest: {help_meta.get('manifest_digest')}",
        f"help_build_id: {help_meta.get('build_id')}",
    ]

    for section in _ordered(data.keys(), SECTION_ORDER):
        lines.append("")
        if section == "machines":
            lines.append(f"## {labels['machines']}")
            machines = data["machines"] or {}
            for machine_id in sorted(machines):
                lines.append(f"### {machine_id}")
                for sub in _ordered(machines[machine_id].keys(), MACHINE_SUBSECTION_ORDER):
                    for key, value in machines[machine_id][sub].items():
                        lines.append(f"- {sub}.{key}: {value}")
            continue
        title = labels["errors"] if section == "errors" else section
        lines.append(f"## {title}")
        for key, value in data[section].items():
            lines.append(f"- {key}: {value}")

    if report.get("checks"):
        lines.append("")
        lines.append(f"## {labels['checks']}")
        for check in report["checks"]:
            lines.append(f"- {check['check_id']}: {check['result']}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_support_service.py -v`
Expected: PASS (21 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/support_service.py backend/tests/test_support_service.py
git commit -m "feat(help): add composable allowlisted support projection"
```

---

### Task 10: Help and support-report API routes

**Files:**
- Modify: `backend/controllers/dev_admin_api.py`
- Test: `backend/tests/test_help_api.py` (API contract **and** application-level failure isolation)

**Interfaces:**
- Consumes: `help_service`, `support_service`, `require_dev_admin`.
- Produces: `GET /api/dev_admin/help/manifest`, `GET /api/dev_admin/help/status`, `POST /api/dev_admin/support_report`.

- [ ] **Step 1: Write the failing test**

Mirror the established pattern in `backend/tests/test_dev_admin_api.py`: the **real**
`backend.flask_server.app`, the same `_basic_auth_headers` helper, and the same
`ADMIN_USERNAME` / `ADMIN_PASSWORD` constants (`"admin"` / `"admin-pass"`). Do not hand-build
a Flask app and do not invent different credentials — Help must have exactly the same
authentication and kill-switch semantics as every other `/api/dev_admin` route.

```python
# backend/tests/test_help_api.py
import base64
import hashlib
import unittest
from unittest.mock import patch

from backend.flask_server import app
from backend.models import init_db, session
from backend.models.setting_model import Settings, update_setting_value
from backend.services import help_service

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin-pass"


def _basic_auth_headers(username: str, password: str) -> dict:
    """The dev/admin blueprint authenticates with HTTP Basic, not X-API-KEY."""

    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


class HelpApiTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(Settings).delete()
        session.commit()
        update_setting_value(session, "api_key", "test-key")
        update_setting_value(session, "dev_admin_enabled", "true")
        update_setting_value(session, "admin_username", ADMIN_USERNAME)
        update_setting_value(
            session, "admin_password_hash",
            hashlib.sha256(ADMIN_PASSWORD.encode("utf-8")).hexdigest(),
        )
        help_service.reset_cache()
        self.client = app.test_client()
        self.headers = _basic_auth_headers(ADMIN_USERNAME, ADMIN_PASSWORD)

    def tearDown(self):
        help_service.reset_cache()

    # ----- identical auth contract to the rest of /api/dev_admin -----

    def test_manifest_requires_credentials(self):
        self.assertEqual(self.client.get("/api/dev_admin/help/manifest").status_code, 401)

    def test_manifest_rejects_wrong_password(self):
        bad = _basic_auth_headers(ADMIN_USERNAME, "wrong")
        self.assertEqual(
            self.client.get("/api/dev_admin/help/manifest", headers=bad).status_code, 401
        )

    def test_kill_switch_returns_403_like_every_other_dev_admin_route(self):
        update_setting_value(session, "dev_admin_enabled", "false")
        resp = self.client.get("/api/dev_admin/help/manifest", headers=self.headers)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(resp.get_json()["disabled"])

    def test_support_report_requires_credentials(self):
        self.assertEqual(
            self.client.post("/api/dev_admin/support_report", json={}).status_code, 401
        )

    # ----- behaviour -----

    def test_manifest_returns_the_compiled_corpus(self):
        payload = self.client.get("/api/dev_admin/help/manifest", headers=self.headers).get_json()
        self.assertTrue(payload["success"])
        self.assertIn("guides", payload["manifest"])

    def test_status_reports_availability(self):
        payload = self.client.get("/api/dev_admin/help/status", headers=self.headers).get_json()
        self.assertTrue(payload["status"]["available"])

    def test_support_report_returns_structured_and_rendered_forms(self):
        resp = self.client.post(
            "/api/dev_admin/support_report",
            json={"locale": "is", "checks": [{"check_id": "c", "result": "ok"}]},
            headers=self.headers,
        )
        payload = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(payload["report"]["checks"][0]["result"], "ok")
        self.assertIn("manifest_digest", payload["report"]["help"])
        self.assertIn("text", payload)

    def test_support_report_ignores_client_supplied_groups(self):
        resp = self.client.post(
            "/api/dev_admin/support_report",
            json={"groups": ["machine.mapping"]},
            headers=self.headers,
        )
        self.assertNotIn("machine.mapping", resp.get_json()["report"]["groups"])


class HelpFailureIsolationTests(unittest.TestCase):
    """Help may fail; the kiosk may not fail because Help failed.

    Asserted at the application level, not by importing a module: a broken manifest
    must leave the real Flask app serving the real kiosk contract.
    """

    def setUp(self):
        init_db()
        session.query(Settings).delete()
        session.commit()
        update_setting_value(session, "api_key", "test-key")
        update_setting_value(session, "dev_admin_enabled", "true")
        update_setting_value(session, "admin_username", ADMIN_USERNAME)
        update_setting_value(
            session, "admin_password_hash",
            hashlib.sha256(ADMIN_PASSWORD.encode("utf-8")).hexdigest(),
        )
        self.client = app.test_client()
        self.headers = _basic_auth_headers(ADMIN_USERNAME, ADMIN_PASSWORD)

    def tearDown(self):
        help_service.reset_cache()

    def _broken(self, **kwargs):
        help_service.reset_cache()
        return patch.object(help_service, "_read_artifact", **kwargs)

    def _assert_kiosk_unaffected(self):
        resp = self.client.get("/api/ui_state", headers={"X-API-KEY": "test-key"})
        self.assertEqual(resp.status_code, 200, "kiosk UI state must survive a Help failure")
        self.assertIn("state", resp.get_json())

    def _assert_help_unavailable(self, reason):
        resp = self.client.get("/api/dev_admin/help/manifest", headers=self.headers)
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.get_json()["reason"], reason)

    def test_missing_manifest_leaves_the_kiosk_serving(self):
        with self._broken(side_effect=FileNotFoundError):
            self._assert_help_unavailable("manifest_missing")
            self._assert_kiosk_unaffected()

    def test_malformed_manifest_leaves_the_kiosk_serving(self):
        with self._broken(return_value="{not json"):
            self._assert_help_unavailable("manifest_unreadable")
            self._assert_kiosk_unaffected()

    def test_unsupported_schema_leaves_the_kiosk_serving(self):
        with self._broken(return_value='{"schema_version": 999, "guides": {}}'):
            self._assert_help_unavailable("schema_version_unsupported")
            self._assert_kiosk_unaffected()

    def test_other_dev_admin_tabs_still_work_while_help_is_broken(self):
        with self._broken(side_effect=OSError("io")):
            for path in ("/api/dev_admin/status", "/api/dev_admin/settings",
                         "/api/dev_admin/machines"):
                self.assertEqual(
                    self.client.get(path, headers=self.headers).status_code, 200,
                    msg=f"{path} must not be affected by a broken Help manifest",
                )

    def test_scanner_and_machine_control_initialise_with_help_broken(self):
        with self._broken(side_effect=OSError("io")):
            help_service.reset_cache()
            self.assertIsNone(help_service.get_manifest())
            from backend.controllers import machine_control, qr_scanner  # noqa: F401
            self.assertIsNotNone(machine_control.UI_STATE.get("state"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_api.py -v`
Expected: FAIL — 404 on `/help/manifest`

- [ ] **Step 3: Write minimal implementation**

Add to the imports in `backend/controllers/dev_admin_api.py`:

```python
from backend.services.help_service import get_manifest as get_help_manifest, get_status as get_help_status
from backend.services.support_service import build_support_report, render_report_text
```

Add the routes immediately before `@dev_admin_api.route("/export-config", methods=["GET"])`:

```python
@dev_admin_api.route("/help/status", methods=["GET"])
@require_dev_admin
def help_status(db):
    return jsonify({"success": True, "status": get_help_status()})


@dev_admin_api.route("/help/manifest", methods=["GET"])
@require_dev_admin
def help_manifest(db):
    manifest = get_help_manifest()
    if manifest is None:
        status = get_help_status()
        return jsonify({
            "success": False,
            "message": "Help content is unavailable.",
            "reason": status.get("reason"),
        }), 503
    return jsonify({"success": True, "manifest": manifest, "status": get_help_status()})


@dev_admin_api.route("/support_report", methods=["POST"])
@require_dev_admin
def support_report(db):
    """Assemble an escalation report.

    Diagnostic groups come from the guide's compiled `diagnostics` list, never from
    the request: a `groups` key in the body is accepted by JSON and then ignored.
    """
    data = request.get_json(silent=True) or {}
    report = build_support_report(
        db,
        guide_id=data.get("guide_id"),
        machine_id=data.get("machine_id"),
        checks=data.get("checks"),
        locale=str(data.get("locale") or "is"),
        locale_shown=data.get("locale_shown"),
    )
    return jsonify({
        "success": True,
        "report": report,
        "text": render_report_text(report, report["locale_requested"]),
    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_api.py -v && python -m pytest backend/tests/ -q`
Expected: PASS (13 tests), full suite green

- [ ] **Step 5: Commit**

```bash
git add backend/controllers/dev_admin_api.py backend/tests/test_help_api.py
git commit -m "feat(help): expose authenticated Help manifest and support-report routes"
```

---

### Task 11: Hash routing for `#help/...`

**Files:**
- Create: `frontend/src/dev-admin/help/helpRouting.js`
- Modify: `frontend/src/dev-admin/DevAdminPage.jsx`, `frontend/src/dev-admin/DevAdminShell.jsx`
- Test: `frontend/src/dev-admin/help/helpRouting.test.js` (run with `node --test`)

**Interfaces:**
- Consumes: `TAB_IDS` from `DevAdminShell.jsx`.
- Produces: `parseHelpHash(hash: string, tabIds: string[]) -> {tab: string, guideId: string|null, anchor: string|null}`; `formatHelpHash(guideId, anchor) -> string`.

Fixes the verified defect: `readTabFromHash` currently returns `'overview'` for any hash it does not recognise, so `#help/machine-unavailable` silently opens the wrong screen.

- [ ] **Step 1: Write the failing test**

```javascript
// frontend/src/dev-admin/help/helpRouting.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseHelpHash, formatHelpHash } from './helpRouting.js';

const TABS = ['overview', 'remote_control', 'diagnostics', 'settings', 'machines', 'help'];

test('plain tab hashes still work', () => {
  assert.deepEqual(parseHelpHash('#settings', TABS), { tab: 'settings', guideId: null, anchor: null });
});

test('unknown hash falls back to overview', () => {
  assert.deepEqual(parseHelpHash('#nonsense', TABS), { tab: 'overview', guideId: null, anchor: null });
});

test('bare help hash opens the help landing', () => {
  assert.deepEqual(parseHelpHash('#help', TABS), { tab: 'help', guideId: null, anchor: null });
});

test('help hash with a guide id is parsed', () => {
  assert.deepEqual(parseHelpHash('#help/machine-unavailable', TABS),
    { tab: 'help', guideId: 'machine-unavailable', anchor: null });
});

test('help hash with a guide id and anchor is parsed', () => {
  assert.deepEqual(parseHelpHash('#help/machine-unavailable/check-telemetry', TABS),
    { tab: 'help', guideId: 'machine-unavailable', anchor: 'check-telemetry' });
});

test('malformed guide ids are rejected rather than passed through', () => {
  assert.equal(parseHelpHash('#help/../../etc/passwd', TABS).guideId, null);
  assert.equal(parseHelpHash('#help/Not Valid', TABS).guideId, null);
});

test('formatHelpHash round-trips', () => {
  assert.equal(formatHelpHash('machine-unavailable', null), '#help/machine-unavailable');
  assert.equal(formatHelpHash('machine-unavailable', 'check-telemetry'),
    '#help/machine-unavailable/check-telemetry');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test src/dev-admin/help/helpRouting.test.js`
Expected: FAIL — cannot find module `./helpRouting.js`

- [ ] **Step 3: Write minimal implementation**

```javascript
// frontend/src/dev-admin/help/helpRouting.js
// Deep links must survive a refresh on a kiosk tablet and must fail visibly when a
// guide id is wrong. The previous parser silently returned 'overview' for anything
// it did not recognise, which would have made every contextual link look broken.

const ID_RE = /^[a-z0-9][a-z0-9-]*$/;

export function parseHelpHash(hash, tabIds) {
  const raw = String(hash || '').replace(/^#/, '');
  const [head, ...rest] = raw.split('/');

  if (head === 'help') {
    const [guideId, anchor] = rest;
    return {
      tab: 'help',
      guideId: guideId && ID_RE.test(guideId) ? guideId : null,
      anchor: anchor && ID_RE.test(anchor) ? anchor : null,
    };
  }
  if (tabIds.includes(head)) {
    return { tab: head, guideId: null, anchor: null };
  }
  return { tab: 'overview', guideId: null, anchor: null };
}

export function formatHelpHash(guideId, anchor) {
  return anchor ? `#help/${guideId}/${anchor}` : `#help/${guideId}`;
}
```

Then in `DevAdminShell.jsx` add `{ id: 'help', label: 'Hjálp' }` to `TABS`, and in
`DevAdminPage.jsx` replace `readTabFromHash` with a call to `parseHelpHash(window.location.hash, TAB_IDS)`,
storing `{tab, guideId, anchor}` in state so the Help tab can open directly on a guide.
An unknown `guideId` (parsed as `null` while the hash had a segment) renders the
Help not-found state from Task 13 rather than redirecting.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test src/dev-admin/help/helpRouting.test.js && npx vite build`
Expected: PASS (7 tests), build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/dev-admin/help/helpRouting.js frontend/src/dev-admin/help/helpRouting.test.js \
        frontend/src/dev-admin/DevAdminPage.jsx frontend/src/dev-admin/DevAdminShell.jsx
git commit -m "fix(dev-admin): parse #help deep links instead of silently opening Overview"
```

---

### Task 12: Client-side search

**Files:**
- Create: `frontend/src/dev-admin/help/helpSearch.js`
- Test: `frontend/src/dev-admin/help/helpSearch.test.js`

**Interfaces:**
- Consumes: the manifest `search` records from Task 5.
- Produces: `fold(text) -> string`, `tokenise(text) -> string[]`, `searchGuides(query, manifest, locale) -> [{guideId, score}]`, `FIELD_WEIGHTS`, `MIN_TOKEN_LEN`.

`fold` must stay byte-identical in behaviour to `backend/help/search_index.py`; the first test pins that with the same fixtures used there.

- [ ] **Step 1: Write the failing test**

```javascript
// frontend/src/dev-admin/help/helpSearch.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fold, tokenise, searchGuides } from './helpSearch.js';

// Same fixtures as backend/tests/test_help_search_index.py — parity is required.
test('folding matches the Python compiler', () => {
  assert.equal(fold('Þvottavél'), 'thvottavel');
  assert.equal(fold('þurrkari'), 'thurrkari');
  assert.equal(fold('aðgengilegur'), 'adgengilegur');
  assert.equal(fold('Ræsir'), 'raesir');
  assert.equal(fold('thvottavel'), fold('þvottavel'));
});

test('tokenise strips punctuation', () => {
  assert.deepEqual(tokenise('Þvottavélin virkar ekki!'), ['thvottavelin', 'virkar', 'ekki']);
});

const MANIFEST = {
  guides: {
    'machine-unavailable': { id: 'machine-unavailable', locales: { is: { title: 'Vélin sýnist upptekin' } } },
    'tune-thresholds': { id: 'tune-thresholds', locales: { is: { title: 'Stilla þröskulda' } } },
  },
  search: {
    'machine-unavailable': { is: { title: ['velin', 'synist', 'upptekin'], aliases: ['thvottavel'],
                                   summary: ['laus'], headings: ['fjarmaeling'], body: ['throskuldur'] } },
    'tune-thresholds': { is: { title: ['stilla', 'throskulda'], aliases: [], summary: [],
                               headings: [], body: ['thvottavel'] } },
  },
};

test('inflected Icelandic query matches the stem via prefix', () => {
  const hits = searchGuides('þvottavélin virkar ekki', MANIFEST, 'is');
  assert.equal(hits[0].guideId, 'machine-unavailable');
});

test('title match outranks a body-only match', () => {
  const hits = searchGuides('þröskulda', MANIFEST, 'is');
  assert.equal(hits[0].guideId, 'tune-thresholds');
});

test('tokens shorter than the minimum do not prefix-match', () => {
  assert.deepEqual(searchGuides('vel', MANIFEST, 'is'), []);
});

test('empty query returns nothing', () => {
  assert.deepEqual(searchGuides('   ', MANIFEST, 'is'), []);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test src/dev-admin/help/helpSearch.test.js`
Expected: FAIL — cannot find module `./helpSearch.js`

- [ ] **Step 3: Write minimal implementation**

```javascript
// frontend/src/dev-admin/help/helpSearch.js
// Icelandic inflection is suffixal, so a stable stem sits at the front of the word.
// Folding plus prefix matching absorbs definite forms, plurals, genitives and
// head-initial compounds without a stemmer or any NLP dependency.
// Keep fold() behaviourally identical to backend/help/search_index.py.

const FOLD_MAP = { þ: 'th', ð: 'd', æ: 'ae', ö: 'o' };
export const MIN_TOKEN_LEN = 4;

export const FIELD_WEIGHTS = { title: 100, aliases: 90, summary: 40, headings: 30, body: 8 };
const PREFIX_PENALTY = 0.6;

const STOPWORDS = new Set([
  'og', 'eda', 'sem', 'thad', 'their', 'ekki', 'vera', 'verdur', 'thegar', 'meira',
  'the', 'and', 'for', 'with', 'that', 'this', 'from', 'your', 'should', 'when',
]);

export function fold(text) {
  const lowered = String(text || '').toLowerCase();
  const expanded = Array.from(lowered).map((c) => FOLD_MAP[c] || c).join('');
  return expanded.normalize('NFD').replace(/[̀-ͯ]/g, '');
}

export function tokenise(text) {
  return (fold(text).match(/[a-z0-9]+/g) || []).filter((t) => t.length >= 2);
}

function scoreToken(token, terms) {
  let best = 0;
  for (const term of terms) {
    if (token === term) return 1;
    if (token.length < MIN_TOKEN_LEN || term.length < MIN_TOKEN_LEN) continue;
    if (token.startsWith(term) || term.startsWith(token)) {
      const shorter = Math.min(token.length, term.length);
      const longer = Math.max(token.length, term.length);
      best = Math.max(best, PREFIX_PENALTY * (shorter / longer));
    }
  }
  return best;
}

export function searchGuides(query, manifest, locale) {
  const tokens = tokenise(query).filter((t) => t.length >= MIN_TOKEN_LEN && !STOPWORDS.has(t));
  if (!tokens.length) return [];

  const results = [];
  for (const [guideId, perLocale] of Object.entries(manifest.search || {})) {
    const record = perLocale[locale] || perLocale[manifest.default_locale] || Object.values(perLocale)[0];
    if (!record) continue;
    let score = 0;
    for (const token of tokens) {
      for (const [field, weight] of Object.entries(FIELD_WEIGHTS)) {
        score += weight * scoreToken(token, record[field] || []);
      }
    }
    if (score > 0) results.push({ guideId, score });
  }
  return results.sort((a, b) => b.score - a.score || a.guideId.localeCompare(b.guideId));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test src/dev-admin/help/helpSearch.test.js`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/dev-admin/help/helpSearch.js frontend/src/dev-admin/help/helpSearch.test.js
git commit -m "feat(help): add folded prefix search for Icelandic queries"
```

---

### Task 13: Block renderer, guide view and UI strings

**Files:**
- Create: `frontend/src/dev-admin/help/helpStrings.js`, `blockDescriptors.js`, `BlockRenderer.jsx`, `GuideView.jsx`, `useHelpManifest.js`
- Modify: `frontend/src/dev-admin/api.js`, `frontend/src/dev-admin/styles/dev-admin.css`
- Test: `frontend/src/dev-admin/help/blockDescriptors.test.js`

**Interfaces:**
- Consumes: manifest guide records.
- Produces: `blockToDescriptor(block) -> descriptor|null` (in `blockDescriptors.js`), `<BlockRenderer blocks={[]} onOpenGuide={fn} />`, `<GuideView guide locale onOpenGuide />`, `useHelpManifest(apiKey) -> {manifest, status, error, loading}`, `STRINGS`, `t(locale, key)`, `resolveLocale(guide, requested) -> {locale, isFallback}`.

`node --test` cannot parse JSX, so all pure conversion logic lives in
`blockDescriptors.js` (plain JS, fully tested) and `BlockRenderer.jsx` is a thin consumer
that only turns descriptors into elements. No component-test toolchain is added.

Draft Icelandic chrome, for review before the feature is considered finished:

| Key | `is` | `en` |
|---|---|---|
| `help` | Hjálp | Help |
| `guides` | Leiðbeiningar | Guides |
| `commonProblems` | Algeng vandamál | Common problems |
| `searchPlaceholder` | Leita í leiðbeiningum | Search guides |
| `relatedGuides` | Tengdar leiðbeiningar | Related guides |
| `copyReport` | Afrita bilanaupplýsingar | Copy support report |
| `reportCopied` | Afritað | Copied |
| `resultOk` | Í lagi | OK |
| `resultProblem` | Vandamál fannst | Problem found |
| `resultUnsure` | Ekki viss | Not sure |
| `resultNotChecked` | Ekki athugað | Not checked |
| `fallbackNotice` | Þessi leiðbeining er ekki enn til á íslensku — sýni enska útgáfu. | This guide is not translated yet — showing the English version. |
| `notFound` | Leiðbeiningin fannst ekki. | Guide not found. |
| `unavailable` | Hjálparefni er ekki tiltækt. | Help content is unavailable. |
| `noResults` | Ekkert fannst. | No results. |
| `riskHigh` | Mikil áhætta | High risk |

- [ ] **Step 1: Write the failing test**

```javascript
// frontend/src/dev-admin/help/blockDescriptors.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { blockToDescriptor } from './blockDescriptors.js';

test('every allowlisted block maps to a descriptor', () => {
  const kinds = ['paragraph', 'heading', 'ordered_list', 'unordered_list',
                 'code_block', 'table', 'callout'];
  for (const type of kinds) {
    assert.ok(blockToDescriptor({ type, inlines: [], items: [], blocks: [], rows: [], header: [] }),
      `no descriptor for ${type}`);
  }
});

test('an unknown block type renders nothing rather than throwing', () => {
  assert.equal(blockToDescriptor({ type: 'script' }), null);
});

test('setting_ref keeps its identifier verbatim', () => {
  const d = blockToDescriptor({ type: 'paragraph',
    inlines: [{ type: 'setting_ref', value: 'telemetry_enabled' }] });
  assert.equal(d.inlines[0].value, 'telemetry_enabled');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test src/dev-admin/help/blockDescriptors.test.js`
Expected: FAIL — cannot find module `./blockDescriptors.js`

- [ ] **Step 3: Write minimal implementation**

Create `helpStrings.js` from the table above with `export function t(locale, key)` falling
back to `en`. Create `useHelpManifest.js` calling a new
`getHelpManifest(apiKey)` in `api.js` (`devAdminRequest('/help/manifest', apiKey)`), caching
the result in a ref and exposing `{manifest, status, error, loading}`; a 503 sets
`error = payload.reason` and never throws.

`blockDescriptors.js` exports the pure `blockToDescriptor(block)`, returning `null` for any
unknown `type` — which is what keeps an unexpected manifest from crashing the panel.
`BlockRenderer.jsx` imports it and switches over the descriptor to render React elements
directly. There is no HTML string anywhere in either file — that is the whole point of the
block schema.

`GuideView.jsx` renders: title, risk badge, the fallback notice when
`resolveLocale()` reports one, the sections, the checklist (Task 14), related guides, and the
support-report button (Task 14).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test src/dev-admin/help/blockDescriptors.test.js && npx vite build`
Expected: PASS (3 tests), build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/dev-admin/help/ frontend/src/dev-admin/api.js frontend/src/dev-admin/styles/dev-admin.css
git commit -m "feat(help): render guides from the strict block schema"
```

---

### Task 14: Checklist evidence and the support-report button

**Files:**
- Create: `frontend/src/dev-admin/help/checklistState.js`, `ChecklistPanel.jsx`, `SupportReportButton.jsx`
- Modify: `frontend/src/dev-admin/api.js`, `frontend/src/dev-admin/help/GuideView.jsx`
- Test: `frontend/src/dev-admin/help/checklistState.test.js`

**Interfaces:**
- Consumes: `guide.locales[locale].checks`.
- Produces: `initialCheckState(checks) -> {[checkId]: 'not_checked'}`, `setCheckResult(state, checkId, result) -> state`, `toReportChecks(state) -> [{check_id, result}]`, `<ChecklistPanel />`, `<SupportReportButton guideId machineId checks locale localeShown />`.

`SupportReportButton` posts `{guide_id, machine_id, checks, locale, locale_shown}` and copies
`payload.text` via `navigator.clipboard`, falling back to a selectable `<textarea>` when the
clipboard API is unavailable (older Chromium on the Pi, or a non-secure origin).

- [ ] **Step 1: Write the failing test**

```javascript
// frontend/src/dev-admin/help/checklistState.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { initialCheckState, setCheckResult, toReportChecks } from './checklistState.js';

const CHECKS = [{ id: 'telemetry-enabled' }, { id: 'current-reading' }];

test('every check starts as not_checked', () => {
  assert.deepEqual(initialCheckState(CHECKS),
    { 'telemetry-enabled': 'not_checked', 'current-reading': 'not_checked' });
});

test('setting a result does not mutate the previous state', () => {
  const before = initialCheckState(CHECKS);
  const after = setCheckResult(before, 'telemetry-enabled', 'problem');
  assert.equal(before['telemetry-enabled'], 'not_checked');
  assert.equal(after['telemetry-enabled'], 'problem');
});

test('invalid results are ignored', () => {
  const state = setCheckResult(initialCheckState(CHECKS), 'telemetry-enabled', 'banana');
  assert.equal(state['telemetry-enabled'], 'not_checked');
});

test('report payload keeps not_checked entries as evidence', () => {
  const state = setCheckResult(initialCheckState(CHECKS), 'current-reading', 'ok');
  assert.deepEqual(toReportChecks(state), [
    { check_id: 'telemetry-enabled', result: 'not_checked' },
    { check_id: 'current-reading', result: 'ok' },
  ]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test src/dev-admin/help/checklistState.test.js`
Expected: FAIL — cannot find module `./checklistState.js`

- [ ] **Step 3: Write minimal implementation**

```javascript
// frontend/src/dev-admin/help/checklistState.js
// "not sure" and "not checked" are evidence, not absences: a developer reading an
// escalation report needs to know which steps the operator could not complete.
export const CHECK_RESULTS = ['ok', 'problem', 'unsure', 'not_checked'];

export function initialCheckState(checks) {
  const state = {};
  for (const check of checks || []) state[check.id] = 'not_checked';
  return state;
}

export function setCheckResult(state, checkId, result) {
  if (!CHECK_RESULTS.includes(result)) return state;
  return { ...state, [checkId]: result };
}

export function toReportChecks(state) {
  return Object.entries(state).map(([check_id, result]) => ({ check_id, result }));
}
```

Then build `ChecklistPanel.jsx` (four result buttons per check, `problem_guide` link shown
when the result is `problem`) and `SupportReportButton.jsx`, and add
`requestSupportReport(apiKey, body)` to `api.js`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test src/dev-admin/help/checklistState.test.js && npx vite build`
Expected: PASS (4 tests), build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/dev-admin/help/ frontend/src/dev-admin/api.js
git commit -m "feat(help): collect checklist evidence and copy support reports"
```

---

### Task 15: Help tab, contextual drawer, and the six integration points

**Files:**
- Create: `frontend/src/dev-admin/help/commonProblems.js`, `HelpPanel.jsx`, `HelpDrawer.jsx`, `ContextualHelpLink.jsx`
- Modify: `DevAdminPage.jsx`, `DiagnosticsPanel.jsx`, `SettingsPanel.jsx`, `MachineDetailDrawer.jsx`, `SecuritySettingsPanel.jsx`, `DangerZonePanel.jsx`, `DevAdminShell.jsx`
- Test: `frontend/src/dev-admin/help/commonProblems.test.js`

**Interfaces:**
- Consumes: `useHelpManifest`, `searchGuides`, `parseHelpHash`, `GuideView`.
- Produces: `commonProblems(manifest, locale) -> [{guideId, title, rank}]`; `<HelpPanel />`; `<HelpDrawer guideId anchor onClose />`; `<ContextualHelpLink guideId anchor label />`.

`ContextualHelpLink` calls `onOpenHelpDrawer(guideId, anchor)` from page context. **It never
changes `window.location.hash` and never switches tabs**, so unsaved Settings drafts, Machine
Card edits, and in-progress technical mapping survive opening Help.

Placements: `MachineDetailDrawer` → `machine-technical-mapping`; `DiagnosticsPanel` live
readings → `tune-thresholds`; each Settings group header → its group guide;
`SecuritySettingsPanel` → `reisa-configuration`; `DangerZonePanel` → `admin-access-recovery`
(replacing the inline recovery prose so there is one source); `DevAdminShell` restart banner →
`settings-requiring-restart`.

- [ ] **Step 1: Write the failing test**

```javascript
// frontend/src/dev-admin/help/commonProblems.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { commonProblems } from './commonProblems.js';

const MANIFEST = {
  default_locale: 'is',
  guides: {
    b: { id: 'b', kind: 'troubleshooting', common_problem_rank: 2, locales: { is: { title: 'B' } } },
    a: { id: 'a', kind: 'troubleshooting', common_problem_rank: 1, locales: { is: { title: 'A' } } },
    c: { id: 'c', kind: 'concept', common_problem_rank: 1, locales: { is: { title: 'C' } } },
    d: { id: 'd', kind: 'troubleshooting', common_problem_rank: null, locales: { is: { title: 'D' } } },
  },
};

test('only ranked troubleshooting guides appear, in rank order', () => {
  assert.deepEqual(commonProblems(MANIFEST, 'is').map((g) => g.guideId), ['a', 'b']);
});

test('concept guides are excluded even when ranked', () => {
  assert.ok(!commonProblems(MANIFEST, 'is').some((g) => g.guideId === 'c'));
});

test('falls back to another locale title when the requested one is absent', () => {
  const m = { ...MANIFEST, guides: { a: { id: 'a', kind: 'troubleshooting',
    common_problem_rank: 1, locales: { en: { title: 'Only English' } } } } };
  assert.equal(commonProblems(m, 'is')[0].title, 'Only English');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && node --test src/dev-admin/help/commonProblems.test.js`
Expected: FAIL — cannot find module `./commonProblems.js`

- [ ] **Step 3: Write minimal implementation**

```javascript
// frontend/src/dev-admin/help/commonProblems.js
// Derived from guide metadata so the landing rail can never drift from the corpus.
export function commonProblems(manifest, locale) {
  return Object.values(manifest.guides || {})
    .filter((g) => g.kind === 'troubleshooting' && Number.isInteger(g.common_problem_rank))
    .map((g) => {
      const payload = g.locales[locale] || g.locales[manifest.default_locale] || Object.values(g.locales)[0];
      return { guideId: g.id, title: payload?.title || g.id, rank: g.common_problem_rank };
    })
    .sort((a, b) => a.rank - b.rank || a.guideId.localeCompare(b.guideId));
}
```

Then build `HelpPanel.jsx` (search box, Common Problems rail, category list, guide view,
`unavailable` and `notFound` states), `HelpDrawer.jsx` (overlay wrapper around `GuideView`),
and `ContextualHelpLink.jsx`; wire drawer state into `DevAdminPage.jsx` and add the six `?`
links.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && node --test src/dev-admin/help/ && npx vite build`
Expected: PASS (all frontend tests), build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/dev-admin/
git commit -m "feat(help): add Help tab, contextual drawer and six help entry points"
```

---

### Task 16: Public bootstrap tier

**Files:**
- Create: `frontend/src/public-help/PublicHelpPage.jsx`
- Create: `docs/public-help/{backend-unavailable,kiosk-screen-blank,network-unavailable}.md`
- Modify: `frontend/src/App.jsx`
- Modify: `backend/tests/test_help_artifacts.py` (extend the snapshot to all three IDs)

**Interfaces:**
- Consumes: `frontend/src/generated/public-help-manifest.json` (imported statically), `BlockRenderer`.
- Produces: `/help` route rendering the public tier with no backend call.

Content constraint, enforced by review and the snapshot test: non-privileged physical checks,
safe retry guidance, and escalation language only. **No admin unlock or re-enable command, no
credential or API-key procedure, no hardware mapping, no relay enablement, no privileged
command.** For lockout the public text is exactly: *"Stjórnandaaðgangur er ekki tiltækur.
Hafðu samband við kerfisstjóra."*

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_help_artifacts.py
    def test_public_tier_contains_exactly_the_reviewed_guides(self):
        import json
        committed = json.loads(cli.PUBLIC_ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(committed["guides"]),
            ["backend-unavailable", "kiosk-screen-blank", "network-unavailable"],
        )

    # NOTE: the privileged-identifier check lives in
    # test_public_manifest_rejects_privileged_identifiers_entirely (Task 7) and now
    # covers all three public guides automatically.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest backend/tests/test_help_artifacts.py -v`
Expected: FAIL — only `backend-unavailable` exists

- [ ] **Step 3: Write the two remaining public guides and the page**

Author `kiosk-screen-blank.md` and `network-unavailable.md` under the constraint above,
recompile, then add to `App.jsx`:

```javascript
const PUBLIC_HELP_PATH = '/help';
// ...
if (window.location.pathname.startsWith(PUBLIC_HELP_PATH)) {
  return <PublicHelpPage />;
}
```

`PublicHelpPage.jsx` imports the generated public manifest directly, so it works with the
backend completely down — which is the only reason this tier exists.

- [ ] **Step 4: Recompile and run the tests**

Run: `source .venv/bin/activate && python -m backend.help.cli && python -m pytest backend/tests/test_help_artifacts.py -v && cd frontend && npx vite build`
Expected: PASS, build succeeds

- [ ] **Step 5: Commit**

```bash
git add docs/public-help/ frontend/src/public-help/ frontend/src/App.jsx \
        frontend/src/generated/ backend/tests/test_help_artifacts.py
git commit -m "feat(help): add public bootstrap help tier at /help"
```

---

### Task 17: Author the 15-guide corpus

**Files:** `docs/admin-guides/en/<category>/<id>.md` (15 canonical) and
`docs/admin-guides/is/<category>/<id>.md` (6 full + 9 stubs).

Work guide-by-guide; commit after each so a bad guide never blocks the rest.

**Tier 1 — full Icelandic (6):**

| id | category | rank |
|---|---|---|
| `machine-unavailable` | machines_telemetry | 1 |
| `machine-does-not-start` | machines_telemetry | 2 |
| `all-machines-available-telemetry-stale` | machines_telemetry | 3 |
| `code-rejected` | codes_reisa | 4 |
| `scanner-not-scanning` | scanner | 5 |
| `kiosk-cannot-reach-backend` | kiosk_display | 6 |

**Tier 2 — English canonical + Icelandic stub (9), each stub `translation_status: published`:** `tune-thresholds`,
`no-telemetry-reading`, `reisa-configuration`, `machine-technical-mapping` (risk high),
`wrong-machine-starts` (risk high), `admin-access-recovery`, `settings-requiring-restart`,
`using-diagnostics`, `admin-panel-orientation`.

Every guide follows the same skeleton, each H2 carrying a stable anchor:
`## When to use this {#when-to-use}` · `## Possible causes {#causes}` ·
`## Steps {#steps}` · `## If this did not fix it {#escalate}`.

Backup/export guidance is a `> [!WARNING]` callout inside `machine-technical-mapping`,
`wrong-machine-starts` and `admin-access-recovery`, and a section in
`admin-panel-orientation` — it does not get its own guide.

Guides `machine-unavailable` and `all-machines-available-telemetry-stale` must cross-link via
`related_guides`: they are adjacent symptoms ("this machine looks busy and isn't" versus
"everything looks free and isn't") and must not duplicate each other's content.

- [ ] **Step 1: For each guide — write the English canonical file**
- [ ] **Step 2: Recompile and confirm validation passes**

Run: `source .venv/bin/activate && python -m backend.help.cli`
Expected: no `CompileError`

- [ ] **Step 3: Write the Icelandic full text (Tier 1) or stub (Tier 2)**

Set `translation_status: review` on every drafted Tier 1 Icelandic file — meaning "drafted,
awaiting maintainer language review" — and **leave it there**. Only the maintainer flips it
to `published`, after reviewing terminology, operator register, and clarity under stress.
The executor must never do so and must never work around the validator to ship them. This is the **per-locale** field from Task 1 —
never the canonical `status`, which describes the guide as a whole and is inherited by
translations.

Consequences, all covered by Task 5's tests:

- An unreviewed Icelandic translation is **withheld from the manifest**, so the guide falls
  back to English with the normal fallback notice. It is not a build failure, so translation
  work can live in the tree without blocking anyone.
- A withheld translation appears in `manifest["excluded_translations"]`, so it is visible and
  assertable rather than silently missing.
- An Icelandic **stub** ships as soon as it is marked `translation_status: published`, which
  is the intended path for the nine Tier 2 guides: discoverable in Icelandic immediately,
  English body, no unreviewed Icelandic prose shown to an operator.
- The canonical locale never needs the field.

Add to Task 18's verification: `manifest["excluded_translations"]` must be empty for the six
Tier 1 guides before beta, and may legitimately be non-empty for Tier 2 work in progress.

- [ ] **Step 4: Recompile, validate, run the full suite**

Run: `source .venv/bin/activate && python -m backend.help.cli && python -m pytest backend/tests/ -q`
Expected: full suite green

- [ ] **Step 5: Commit per guide**

```bash
git add docs/admin-guides/ backend/help/generated/
git commit -m "docs(help): add <guide-id> guide"
```

---

### Task 18: Documentation and final verification

**Files:**
- Create: `docs/admin-guides/README.md`
- Modify: `CLAUDE.md`, `docs/README.md`, `docs/reference/api-reference.md`, `docs/ai/system-quick-map.md`, `docs/operations/runbooks/beta-dev-admin-panel.md`

- [ ] **Step 1: Write the authoring guide**

`docs/admin-guides/README.md` covers: the frontmatter schema, the canonical/inheritance rule,
stub authoring, the H2 anchor convention, the checklist schema, the allowed Markdown subset,
`guide:` links, `python -m backend.help.cli`, and the rule that the operator corpus is derived
from the runbooks rather than mirroring them.

- [ ] **Step 2: Update the reference docs**

Add the three endpoints to `api-reference.md`; add Help Hub routing to `system-quick-map.md`;
document the Help tab and contextual links in `beta-dev-admin-panel.md`; add the compile
command to `CLAUDE.md` next to the test commands.

- [ ] **Step 3: Verify the translation review gate**

```bash
source .venv/bin/activate
python - <<'CHECK'
import json
from backend.help import cli
m = json.loads(cli.ADMIN_ARTIFACT.read_text(encoding="utf-8"))
tier1 = ["machine-unavailable", "machine-does-not-start",
         "all-machines-available-telemetry-stale", "code-rejected",
         "scanner-not-scanning", "kiosk-cannot-reach-backend"]
withheld = {(e["guide_id"], e["locale"]) for e in m["excluded_translations"]}
missing = [g for g in tier1 if (g, "is") in withheld or "is" not in m["guides"][g]["locales"]]
print("Tier 1 guides without published Icelandic:", missing or "none")
print("withheld translations:", sorted(withheld) or "none")
CHECK
```

Expected before beta: no Tier 1 guide lacks published Icelandic.

- [ ] **Step 4: Run the whole verification set**

```bash
source .venv/bin/activate
sha256sum codes.db frontend/.env                  # record before
python -m backend.help.cli --check                # must exit 0
python -m pytest backend/tests/ -q
python -m unittest discover -s backend/tests -t .
python -m compileall -q backend
cd frontend && node --test src/dev-admin/help/ && npx vite build
sha256sum codes.db frontend/.env                  # must be unchanged
```

Expected: `--check` exits 0; pytest and unittest green; build succeeds; both hashes identical.

- [ ] **Step 5: Manual verification of the three untestable behaviours**

With the backend and Vite running, in `/dev/admin`:

1. Settings → edit a value without saving → click a group `?` → confirm the drawer opens and
   the unsaved value is still there after closing it.
2. Machine Cards → open Advanced/Technical Mapping → change a field → click its `?` → confirm
   the drawer opens and the in-progress mapping edit survives.
3. Navigate to `#help/no-such-guide` → confirm the Help not-found state renders and the panel
   does **not** silently fall back to Overview.

- [ ] **Step 6: Confirm the kiosk is untouched**

Run the kiosk flow check from the pre-merge review: scan → select → start with
`backend_relay_enabled=false`, confirming no relay command is issued and `/dev/kiosk-preview`
still renders.

- [ ] **Step 7: Commit**

```bash
git add docs/ CLAUDE.md
git commit -m "docs(help): document the Help Hub authoring and API surface"
```

---

## Testing strategy and its one honest gap

The backend is covered by `pytest`/`unittest` exactly like the existing 96 tests. The
frontend has **no component test infrastructure** — `frontend/package.json` carries no jest,
vitest, testing-library or jsdom, and this plan deliberately does not add one, because
introducing a second test toolchain immediately before physical beta is a worse risk than the
gap it closes.

Consequently every frontend test in this plan runs under `node --test` against **pure
functions only**: `helpRouting.js`, `helpSearch.js`, `checklistState.js`, `commonProblems.js`,
and `blockDescriptors.js`. That is deliberate — the genuinely error-prone logic (hash parsing,
Icelandic folding and scoring, evidence state, rank derivation, block allowlisting) is all
pure and therefore all covered.

What it does **not** cover is React component behaviour. These three behaviours must be
verified by hand in Task 18, and must not be claimed as passing on the strength of the
automated suite:

1. Opening contextual Help from Settings with unsaved edits leaves the draft intact.
2. Opening contextual Help from `MachineDetailDrawer` mid-edit leaves the technical mapping
   draft intact.
3. `#help/<unknown-id>` renders the not-found state rather than Overview.

If component testing is added later, these three are the first cases to automate.

## Explicitly out of scope

Do not build any of these, even if a task seems to invite it: AI assistant, embeddings or
vector store; the `restart_backend` action or any process control; a decision-tree engine,
`if_true`/`if_false` routing, or conditional evaluation; a feedback table or analytics
storage; system-aware live-status cards inside guides; translating the rest of the admin UI;
folding `settingHelp.js` into the backend schema; code-splitting `DevAdminPage`; a guide
editor or CMS; any endpoint accepting a filesystem path.

## Known deliberate limitations

- Authenticated recovery Help is unreachable during a genuine admin lockout; the public tier
  gives escalation language only.
- The Hub converts roughly a quarter of support cases on its own — the restart gap remains the
  largest self-service lever and stays deferred until a supervised systemd service exists.
- Code splitting is desirable hygiene, **not** a security boundary; admin content is protected
  by authentication alone.
- `settingHelp.js` duplication with `SETTING_SCHEMA.description` remains post-beta debt; the
  Hub must not become a third description source.
- Nine Tier 2 guides ship as Icelandic discovery stubs; full translation follows measured
  `locale_shown` fallback frequency.
