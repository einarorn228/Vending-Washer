# backend/tests/test_support_service.py
import re
import unittest
from unittest import mock

from backend.controllers.telemetry import (
    RUNSTATE_AVAILABLE,
    DeviceInfo,
    MachineConfigInfo,
    MachineRuntime,
    MachineStateStore,
)
from backend.models import Session, init_db
from backend.models.setting_model import update_setting_value
from backend.services import support_service
from backend.services.dev_admin_service import SECRET_KEYS


def _seed_two_machines():
    config = MachineConfigInfo(on_threshold=8, off_threshold=3, on_confirm_ms=1200,
                               off_confirm_ms=3000, poll_interval_ms=1000)
    washer_dev = DeviceInfo(id=3, name="Washer UNI", role="washer_uni", model="shelly-uni",
                            ip="192.0.2.11", relay_channel=0, input_channel=None, metric_source="voltage")
    dryer_dev = DeviceInfo(id=4, name="Dryer UNI", role="dryer_uni", model="shelly-uni",
                           ip="192.0.2.12", relay_channel=0, input_channel=None, metric_source="power")
    MachineStateStore.instance().update_definitions({
        "washer1": MachineRuntime(db_id=1, slug="washer1", ui_name="Washer 1", uni_device=washer_dev,
                                  config=config, i4_device_id=None, i4_button_index=0,
                                  is_enabled=True, run_state=RUNSTATE_AVAILABLE),
        "dryer1": MachineRuntime(db_id=2, slug="dryer1", ui_name="Dryer 1", uni_device=dryer_dev,
                                 config=config, i4_device_id=None, i4_button_index=1,
                                 is_enabled=True, run_state=RUNSTATE_AVAILABLE),
    }, {})


class SupportReportTests(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = Session()
        update_setting_value(self.db, "api_key", "super-secret-key")
        update_setting_value(self.db, "reisa_bearer_token", "super-secret-token")
        update_setting_value(self.db, "telemetry_enabled", "true")

    def tearDown(self):
        MachineStateStore.instance().update_definitions({}, {})
        self.db.close()

    def test_core_report_needs_no_guide(self):
        report = support_service.build_support_report(self.db)
        self.assertIn("generated_at", report)
        self.assertIn("kiosk", report["data"])
        self.assertIsNone(report["guide_id"])

    def test_secret_values_never_appear_anywhere(self):
        _seed_two_machines()
        blob = repr(support_service.build_support_report(
            self.db, groups=tuple(support_service.GROUP_HANDLERS)
        ))
        self.assertNotIn("super-secret-key", blob)
        self.assertNotIn("super-secret-token", blob)

    def test_secrets_are_presence_only(self):
        report = support_service.build_support_report(self.db)
        self.assertIs(report["data"]["provider"]["reisa_token_configured"], True)

    def test_every_secret_key_is_excluded_from_the_safe_allowlist(self):
        for key in SECRET_KEYS:
            self.assertNotIn(key, support_service.SAFE_SETTING_KEYS)

    def test_all_four_machine_groups_compose_without_loss(self):
        """Guards the bug where four groups describing the same machines were merged
        with dict.update() and only the last survived."""
        _seed_two_machines()
        report = support_service.build_support_report(
            self.db,
            groups=("machine.identity", "machine.telemetry", "machine.thresholds", "machine.mapping"),
        )
        machines = report["data"]["machines"]
        self.assertEqual(sorted(machines), ["dryer1", "washer1"])
        for machine_id, sections in machines.items():
            self.assertEqual(sorted(sections), ["identity", "mapping", "telemetry", "thresholds"],
                             msg=f"machine {machine_id} lost a diagnostic group")

    def test_machine_sections_carry_their_own_fields(self):
        _seed_two_machines()
        report = support_service.build_support_report(
            self.db, groups=("machine.identity", "machine.telemetry", "machine.thresholds", "machine.mapping")
        )
        washer = report["data"]["machines"]["washer1"]
        self.assertEqual(washer["identity"]["name"], "Washer 1")
        self.assertIn("run_state", washer["identity"])
        self.assertIn("last_value", washer["telemetry"])
        self.assertEqual(washer["thresholds"]["config"]["on_threshold"], 8)
        self.assertEqual(washer["mapping"]["device"]["ip"], "192.0.2.11")

    def test_report_carries_knowledge_provenance(self):
        report = support_service.build_support_report(self.db)
        self.assertIn("help", report)
        self.assertIn("schema_version", report["help"])
        self.assertIn("manifest_digest", report["help"])
        self.assertIn("build_id", report["help"])

    # ----- locale_shown is server-owned -----

    def _guide(self, canonical="en", locales=None, checks=None):
        """Synthetic compiled guide for locale/checklist derivation tests."""
        payload = {}
        for loc, kind in (locales or {"en": "full"}).items():
            if kind == "full":
                payload[loc] = {"stub": False, "translation_status": "published",
                                "sections": [], "checks": checks or []}
            elif kind == "stub":
                payload[loc] = {"stub": True, "translation_status": "published"}
        return {"id": "g", "canonical_locale": canonical, "diagnostics": [], "locales": payload}

    def test_locale_shown_is_requested_when_full_translation_exists(self):
        guide = self._guide(locales={"en": "full", "is": "full"})
        self.assertEqual(support_service.resolve_locale_shown(guide, "is"), "is")

    def test_locale_shown_falls_back_to_canonical_for_a_stub(self):
        guide = self._guide(locales={"en": "full", "is": "stub"})
        self.assertEqual(support_service.resolve_locale_shown(guide, "is"), "en")

    def test_locale_shown_falls_back_to_canonical_when_translation_withheld_or_absent(self):
        guide = self._guide(locales={"en": "full"})   # `is` withheld/absent
        self.assertEqual(support_service.resolve_locale_shown(guide, "is"), "en")

    def test_locale_shown_is_requested_for_canonical_locale(self):
        guide = self._guide(locales={"en": "full"})
        self.assertEqual(support_service.resolve_locale_shown(guide, "en"), "en")

    def test_locale_shown_without_a_guide_is_the_requested_locale(self):
        report = support_service.build_support_report(self.db, locale="is")
        self.assertEqual(report["locale_requested"], "is")
        self.assertEqual(report["locale_shown"], "is")

    def test_report_derives_locale_shown_from_the_resolved_guide(self):
        from unittest.mock import patch
        guide = self._guide(locales={"en": "full", "is": "stub"})
        with patch.object(support_service, "get_guide", return_value=guide):
            report = support_service.build_support_report(self.db, guide_id="g", locale="is")
        self.assertEqual(report["locale_requested"], "is")
        self.assertEqual(report["locale_shown"], "en")

    # ----- machine_id is normalised provenance -----

    def test_reported_machine_id_is_normalised_or_null(self):
        _seed_two_machines()
        cases = [(" dryer1 ", "dryer1"), ("dryer1", "dryer1"), ("no-such", None),
                 ("", None), ("   ", None), ({}, None), ([], None), (0, None),
                 (7, None), (None, None)]
        for raw, expected in cases:
            with self.subTest(machine_id=raw):
                report = support_service.build_support_report(
                    self.db, machine_id=raw, groups=("machine.identity",))
                self.assertEqual(report["machine_id"], expected)
                if expected:
                    self.assertEqual(sorted(report["data"]["machines"]), [expected])

    # ----- checklist evidence belongs to the guide -----

    def test_checks_are_discarded_without_a_guide(self):
        report = support_service.build_support_report(
            self.db, checks=[{"check_id": "telemetry-enabled", "result": "ok"}])
        self.assertEqual(report["checks"], [])

    def test_only_checks_declared_by_the_guide_survive(self):
        from unittest.mock import patch
        guide = self._guide(checks=[{"id": "telemetry-enabled"}, {"id": "current-reading"}])
        with patch.object(support_service, "get_guide", return_value=guide):
            report = support_service.build_support_report(self.db, guide_id="g", checks=[
                {"check_id": "telemetry-enabled", "result": "ok"},
                {"check_id": "invented", "result": "problem"},
                {"check_id": "current-reading", "result": "banana"},
                {"check_id": "current-reading", "result": "unsure"},
            ])
        self.assertEqual(report["checks"], [
            {"check_id": "telemetry-enabled", "result": "ok"},
            {"check_id": "current-reading", "result": "unsure"},
        ])

    def test_check_evidence_is_capped(self):
        from unittest.mock import patch
        guide = self._guide(checks=[{"id": "c"}])
        flood = [{"check_id": "c", "result": "ok"}] * (support_service.MAX_CHECKS + 20)
        with patch.object(support_service, "get_guide", return_value=guide):
            report = support_service.build_support_report(self.db, guide_id="g", checks=flood)
        self.assertLessEqual(len(report["checks"]), support_service.MAX_CHECKS)

    def test_unknown_guide_id_falls_back_to_core_groups(self):
        report = support_service.build_support_report(self.db, guide_id="../../etc/passwd")
        self.assertIsNone(report["guide_id"])
        self.assertIn("kiosk", report["data"])

    def test_checklist_evidence_is_carried_through(self):
        # Checklist evidence only survives when it belongs to a resolved guide
        # (boundary rule 3), so this pins the "carried through" half of that rule
        # against a guide that declares the check_id being reported.
        from unittest.mock import patch
        guide = self._guide(checks=[{"id": "telemetry-enabled"}])
        with patch.object(support_service, "get_guide", return_value=guide):
            report = support_service.build_support_report(
                self.db, guide_id="g",
                checks=[{"check_id": "telemetry-enabled", "result": "problem"}],
            )
        self.assertEqual(report["checks"][0]["result"], "problem")

    def test_invalid_check_result_is_dropped(self):
        from unittest.mock import patch
        guide = self._guide(checks=[{"id": "c"}])
        with patch.object(support_service, "get_guide", return_value=guide):
            report = support_service.build_support_report(
                self.db, guide_id="g",
                checks=[{"check_id": "c", "result": "banana"}, {"check_id": "c", "result": {}},
                        {"check_id": "c", "result": []}, {"check_id": " c ", "result": "ok"}],
            )
        self.assertEqual(report["checks"], [{"check_id": "c", "result": "ok"}])

    # ----- machine scoping -----

    def test_unknown_or_malformed_machine_id_narrows_to_nothing(self):
        """A bad machine_id must never widen the report to every machine."""
        _seed_two_machines()
        groups = ("machine.identity", "machine.telemetry")
        for bad in ("no-such-machine", "", "   ", {}, [], 0, 7):
            with self.subTest(machine_id=bad):
                report = support_service.build_support_report(self.db, machine_id=bad, groups=groups)
                self.assertEqual(report["data"].get("machines", {}), {})

    def test_none_machine_id_means_unscoped(self):
        _seed_two_machines()
        report = support_service.build_support_report(
            self.db, machine_id=None, groups=("machine.identity",)
        )
        self.assertEqual(set(report["data"].get("machines", {})), {"dryer1", "washer1"})

    # ----- authorisation boundary -----

    def test_core_report_never_includes_mapping(self):
        _seed_two_machines()
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
        _seed_two_machines()
        report = support_service.build_support_report(
            self.db, groups=tuple(support_service.GROUP_HANDLERS)
        )
        text = support_service.render_report_text(report, "is")
        self.assertIn("Vending-Washer", text)
        self.assertNotIn("super-secret-key", text)
        self.assertRegex(text, r"help_manifest_digest: [0-9a-f]{12}")

    def test_settings_group_rejects_non_allowlisted_keys_at_definition(self):
        with self.assertRaises(ValueError):
            support_service._settings_group(("api_key",))
        with self.assertRaises(ValueError):
            support_service._settings_group(("telemetry_enabled", "reisa_bearer_token"))

    def test_malformed_guide_id_falls_back_to_core_without_raising(self):
        for bad in ({"a": 1}, ["x"], 7, "", "   "):
            with self.subTest(guide_id=bad):
                report = support_service.build_support_report(self.db, guide_id=bad)
                self.assertIsNone(report["guide_id"])
                self.assertEqual(report["groups"], list(support_service.CORE_GROUPS))



class MachineProjectionAllowlistTests(unittest.TestCase):
    """The nested device/config dicts must be projected field by field.

    _MACHINE_SECTIONS used to forward MachineStateStore.get_diagnostic_snapshot()'s
    whole "device" and "config" dicts. Anything added to either upstream would then have
    shipped in every escalation report with no review. These tests fail if that ever
    comes back.
    """

    # A snapshot row shaped exactly like get_diagnostic_snapshot() produces, with two
    # fields nobody allowlisted planted inside the nested dicts.
    ROW = {
        "id": "washer1",
        "name": "Washer 1",
        "is_enabled": True,
        "available": True,
        "run_state": "available",
        "pending_start": False,
        "last_value": 7.5,
        "band": "mid",
        "seconds_since_read": 1.0,
        "seconds_above": None,
        "seconds_below": None,
        "device": {
            "name": "Washer UNI",
            "ip": "192.0.2.11",
            "metric_source": "voltage",
            "relay_channel": 0,
            "auth_password": "shelly-device-password",
            "future_field": "added upstream later",
        },
        "config": {
            "on_threshold": 8,
            "off_threshold": 3,
            "on_confirm_ms": 1200,
            "off_confirm_ms": 3000,
            "poll_interval_ms": 1000,
            "internal_note": "not reviewed for disclosure",
        },
        "secret_top_level": "must never appear",
    }

    def setUp(self):
        init_db()
        self.db = Session()
        self._patch = mock.patch.object(support_service, "_snapshot", return_value=[self.ROW])
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self.db.close()

    def _report(self):
        return support_service.build_support_report(
            self.db, groups=("machine.identity", "machine.telemetry",
                             "machine.thresholds", "machine.mapping")
        )

    def _machine(self):
        return self._report()["data"]["machines"]["washer1"]

    def test_unallowlisted_device_field_never_reaches_the_report(self):
        blob = repr(self._report())
        self.assertNotIn("shelly-device-password", blob)
        self.assertNotIn("auth_password", blob)
        self.assertNotIn("future_field", blob)

    def test_unallowlisted_config_field_never_reaches_the_report(self):
        blob = repr(self._report())
        self.assertNotIn("internal_note", blob)
        self.assertNotIn("not reviewed for disclosure", blob)

    def test_unallowlisted_top_level_field_never_reaches_the_report(self):
        self.assertNotIn("secret_top_level", repr(self._report()))

    def test_the_named_device_fields_are_still_present(self):
        """The allowlist must not have been tightened into uselessness."""
        device = self._machine()["mapping"]["device"]
        self.assertEqual(set(device), {"name", "ip", "metric_source", "relay_channel"})
        # The LAN IP is intentionally reported; this pins that as a decision.
        self.assertEqual(device["ip"], "192.0.2.11")

    def test_the_named_config_fields_are_still_present(self):
        config = self._machine()["thresholds"]["config"]
        self.assertEqual(
            set(config),
            {"on_threshold", "off_threshold", "on_confirm_ms", "off_confirm_ms",
             "poll_interval_ms"},
        )
        self.assertEqual(config["on_threshold"], 8)

    def test_report_shape_is_unchanged_by_the_allowlist(self):
        machine = self._machine()
        self.assertEqual(set(machine), {"identity", "telemetry", "thresholds", "mapping"})
        self.assertEqual(set(machine["identity"]),
                         {"name", "is_enabled", "available", "run_state", "pending_start"})

    def test_a_nested_value_that_is_not_a_dict_is_dropped_not_forwarded(self):
        row = dict(self.ROW, device="192.0.2.11 leaked as a bare string")
        with mock.patch.object(support_service, "_snapshot", return_value=[row]):
            report = support_service.build_support_report(self.db, groups=("machine.mapping",))
        self.assertNotIn("leaked as a bare string", repr(report))
        self.assertEqual(report["data"]["machines"]["washer1"]["mapping"], {})

    def test_allowlist_matches_the_dicts_the_store_actually_builds(self):
        """Catches an upstream rename silently emptying a report section."""
        _seed_two_machines()
        rows = MachineStateStore.instance().get_diagnostic_snapshot()
        row = next(r for r in rows if r["id"] == "washer1")
        for section, key in (("machine.mapping", "device"), ("machine.thresholds", "config")):
            with self.subTest(section=section):
                _, fields = support_service._MACHINE_SECTIONS[section]
                allowed = dict(f for f in fields if isinstance(f, tuple))[key]
                missing = set(allowed) - set(row[key])
                self.assertEqual(
                    missing, set(),
                    f"{section} allowlists {sorted(missing)}, which "
                    f"get_diagnostic_snapshot() no longer puts in {key!r}.",
                )
        MachineStateStore.instance().update_definitions({}, {})


if __name__ == "__main__":
    unittest.main()
