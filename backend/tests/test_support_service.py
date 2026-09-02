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
