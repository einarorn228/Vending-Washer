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

    def test_stray_indented_top_level_key_is_a_compile_error(self):
        with self.assertRaises(CompileError):
            split_frontmatter("---\nid: g\n  locale: en\n---\nbody\n")

    def test_orphan_indented_line_after_string_list_is_a_compile_error(self):
        with self.assertRaises(CompileError):
            split_frontmatter(
                "---\nid: g\nrelated_guides:\n  - a\n  bogus: orphan\n---\nbody\n"
            )

    def test_indented_continuation_inside_checks_entry_still_parses(self):
        meta, _ = split_frontmatter(
            "---\nid: g\nchecks:\n  - id: c1\n    question: Q\n    route: diagnostics\n---\nbody\n"
        )
        self.assertEqual(meta["checks"][0]["route"], "diagnostics")


if __name__ == "__main__":
    unittest.main()
