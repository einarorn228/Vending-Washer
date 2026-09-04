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

    def test_translation_may_list_inherited_fields_in_any_order(self):
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("related_settings:\n  - telemetry_enabled",
                          "related_settings:\n  - telemetry_enabled\n  - backend_relay_enabled"))
        _write(self.tmp, "is/machines_telemetry/machine-unavailable.md",
               IS_STUB_PUBLISHED.replace(
                   "search_aliases:",
                   "related_settings:\n  - backend_relay_enabled\n  - telemetry_enabled\nsearch_aliases:"))
        self.settings = {"telemetry_enabled", "backend_relay_enabled"}
        guide = self.compile()["guides"]["machine-unavailable"]
        self.assertEqual(guide["related_settings"], ["backend_relay_enabled", "telemetry_enabled"])

    def test_missing_last_reviewed_is_a_compile_error(self):
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("last_reviewed: 2026-09-02\n", ""))
        with self.assertRaises(CompileError):
            self.compile()

    def test_check_without_id_is_a_compile_error(self):
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("---\n\n## Check telemetry",
                          "checks:\n  - question: Is it on?\n---\n\n## Check telemetry"))
        with self.assertRaises(CompileError):
            self.compile()

    def test_check_diagnostics_group_is_validated(self):
        checks = ("checks:\n  - id: telemetry-enabled\n"
                  "    question: Is it on?\n    diagnostics: {group}\n")
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("---\n\n## Check telemetry",
                          checks.format(group="machine.telemetry") + "---\n\n## Check telemetry"))
        self.assertEqual(
            self.compile()["guides"]["machine-unavailable"]["locales"]["en"]["checks"][0]["diagnostics"],
            "machine.telemetry",
        )
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("---\n\n## Check telemetry",
                          checks.format(group="nonsense.group") + "---\n\n## Check telemetry"))
        with self.assertRaises(CompileError):
            self.compile()

    def test_scalar_in_list_field_is_a_compile_error(self):
        _write(self.tmp, "en/machines_telemetry/machine-unavailable.md",
               EN.replace("related_settings:\n  - telemetry_enabled",
                          "related_settings: telemetry_enabled"))
        with self.assertRaises(CompileError):
            self.compile()

    def test_scalar_search_alias_in_translation_is_a_compile_error(self):
        _write(self.tmp, "is/machines_telemetry/machine-unavailable.md",
               IS_STUB_PUBLISHED.replace("search_aliases:\n  - þvottavél",
                                         "search_aliases: þvottavél"))
        with self.assertRaises(CompileError):
            self.compile()

    def test_readme_is_not_treated_as_a_guide(self):
        """Authoring docs live in the guide tree; they must not need frontmatter.

        `docs/admin-guides/README.md` is prose for guide authors. Without the
        reserved-filename skip the compiler would demand a frontmatter block from it
        and no manifest would be written at all.
        """
        _write(self.tmp, "README.md", "# Authoring guides\n\nNo frontmatter here.\n")
        _write(self.tmp, "en/README.md", "# Locale notes\n\nStill no frontmatter.\n")
        manifest = self.compile()
        self.assertEqual(sorted(manifest["guides"]), ["machine-unavailable"])
        self.assertEqual(manifest["guide_count"], 1)


if __name__ == "__main__":
    unittest.main()
