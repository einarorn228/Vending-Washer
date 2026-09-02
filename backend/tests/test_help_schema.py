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
