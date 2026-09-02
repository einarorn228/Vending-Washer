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
