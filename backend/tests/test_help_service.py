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

    def test_non_object_json_degrades_without_raising(self):
        for payload in ("[]", "42", "null", '"a string"'):
            with self.subTest(payload=payload):
                help_service.reset_cache()
                with patch.object(help_service, "_read_artifact", return_value=payload):
                    self.assertIsNone(help_service.get_manifest())
                    status = help_service.get_status()
                self.assertFalse(status["available"])
                self.assertEqual(status["reason"], "manifest_unreadable")

    def test_malformed_guides_field_degrades_without_raising(self):
        for guides in ("[]", "null", '"text"', "7"):
            with self.subTest(guides=guides):
                help_service.reset_cache()
                payload = '{"schema_version": 1, "guides": ' + guides + '}'
                with patch.object(help_service, "_read_artifact", return_value=payload):
                    self.assertIsNone(help_service.get_manifest())
                    self.assertIsNone(help_service.get_guide("anything"))
                    status = help_service.get_status()
                self.assertFalse(status["available"])
                self.assertEqual(status["reason"], "manifest_unreadable")


if __name__ == "__main__":
    unittest.main()
