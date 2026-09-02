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

    def test_multi_paragraph_list_item_parses(self):
        sections = parse_body("## S {#s}\n\n- a\n\n  second para in a\n\n- b\n", SETTINGS)
        lst = next(b for b in sections[0]["blocks"] if b["type"] == "unordered_list")
        self.assertEqual(len(lst["items"]), 2)
        self.assertEqual(len(lst["items"][0]), 2, "first item should hold two paragraphs")

    def test_callout_with_blank_separator_line_parses(self):
        sections = parse_body("## S {#s}\n\n> [!WARNING]\n>\n> Careful.\n", SETTINGS)
        callout = next(b for b in sections[0]["blocks"] if b["type"] == "callout")
        self.assertEqual(callout["level"], "warning")

    def test_callout_body_has_no_marker_or_stray_whitespace(self):
        sections = parse_body("## S {#s}\n\n> [!WARNING]\n> Careful.\n", SETTINGS)
        callout = next(b for b in sections[0]["blocks"] if b["type"] == "callout")
        inlines = callout["blocks"][0]["inlines"]
        texts = [i["text"] for i in inlines if i["type"] == "text"]
        self.assertEqual(texts, ["Careful."])


if __name__ == "__main__":
    unittest.main()
