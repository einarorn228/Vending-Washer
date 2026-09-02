import base64
import hashlib
import unittest

from backend.controllers.telemetry import (
    DeviceInfo,
    MachineConfigInfo,
    MachineRuntime,
    MachineStateStore,
    RUNSTATE_AVAILABLE,
)
from backend.controllers import machine_control
from backend.flask_server import app
from backend.models import init_db, session
from backend.models.device_model import Device
from backend.models.machine_model import Machine, MachineConfig
from backend.models.setting_model import Settings, get_setting_value, update_setting_value
from backend.models.settings_audit_model import SettingsAuditLog
from backend.services.dev_admin_service import LOCKOUT_CONFIRMATION_PHRASE


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin-pass"


def _basic_auth_headers(username: str, password: str) -> dict:
    """The dev/admin blueprint authenticates with HTTP Basic, not X-API-KEY."""

    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


class DevAdminApiTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(MachineConfig).delete()
        session.query(Machine).delete()
        session.query(Device).delete()
        session.query(Settings).delete()
        session.query(SettingsAuditLog).delete()
        session.commit()
        update_setting_value(session, "api_key", "test-key")
        update_setting_value(session, "dev_admin_enabled", "true")
        update_setting_value(session, "button_box_enabled", "false")
        update_setting_value(session, "backend_relay_enabled", "false")
        update_setting_value(session, "telemetry_enabled", "true")
        update_setting_value(session, "api_key", "test-key")
        update_setting_value(session, "admin_username", ADMIN_USERNAME)
        update_setting_value(
            session,
            "admin_password_hash",
            hashlib.sha256(ADMIN_PASSWORD.encode("utf-8")).hexdigest(),
        )
        update_setting_value(session, "reisa_bearer_token", "secret-token")

        self.i4 = Device(name="i4", role="i4", model="shelly-plus-i4", ip="192.168.1.5", input_channel=0, metric_source="digital")
        self.dev1 = Device(name="Washer UNI", role="washer_uni", model="shelly-uni", ip="192.168.1.11", relay_channel=0, metric_source="voltage")
        self.dev2 = Device(name="Dryer UNI", role="dryer_uni", model="shelly-uni", ip="192.168.1.12", relay_channel=0, metric_source="power")
        session.add_all([self.i4, self.dev1, self.dev2])
        session.flush()
        self.m1 = Machine(name="washer1", ui_name="Washer 1", uni_device_id=self.dev1.id, uni_relay_channel=0, i4_device_id=self.i4.id, i4_button_index=0, is_enabled=1)
        self.m2 = Machine(name="dryer1", ui_name="Dryer 1", uni_device_id=self.dev2.id, uni_relay_channel=0, i4_device_id=self.i4.id, i4_button_index=1, is_enabled=1)
        session.add_all([self.m1, self.m2])
        session.flush()
        session.add_all([
            MachineConfig(machine_id=self.m1.id, on_threshold=8, off_threshold=3, on_confirm_ms=1200, off_confirm_ms=3000, poll_interval_ms=1000),
            MachineConfig(machine_id=self.m2.id, on_threshold=8, off_threshold=3, on_confirm_ms=1200, off_confirm_ms=3000, poll_interval_ms=1000),
        ])
        session.commit()

        app.config["TESTING"] = True
        self.client = app.test_client()
        self.headers = _basic_auth_headers(ADMIN_USERNAME, ADMIN_PASSWORD)

    def tearDown(self):
        MachineStateStore.instance().update_definitions({}, {})

    def test_kill_switch_returns_403(self):
        update_setting_value(session, "dev_admin_enabled", "false")
        resp = self.client.get("/api/dev_admin/status", headers=self.headers)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(resp.get_json()["disabled"])

    def test_unlock_requires_valid_admin_credentials(self):
        resp = self.client.post(
            "/api/dev_admin/unlock",
            headers=_basic_auth_headers(ADMIN_USERNAME, "wrong-password"),
        )
        self.assertEqual(resp.status_code, 401)
        resp = self.client.post(
            "/api/dev_admin/unlock",
            headers=_basic_auth_headers("not-the-admin", ADMIN_PASSWORD),
        )
        self.assertEqual(resp.status_code, 401)
        resp = self.client.post("/api/dev_admin/unlock")
        self.assertEqual(resp.status_code, 401)
        resp = self.client.post("/api/dev_admin/unlock", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

    def test_settings_hide_secrets(self):
        resp = self.client.get("/api/dev_admin/settings", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        settings = {s["key"]: s for g in payload["groups"] for s in g["settings"]}
        self.assertIsNone(settings["api_key"]["value"])
        self.assertTrue(settings["api_key"]["is_set"])
        self.assertIsNone(settings["reisa_bearer_token"]["value"])

    def test_secret_update_requires_current_api_key(self):
        # Missing current_api_key.
        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"api_key": "new"}},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(get_setting_value(session, "api_key"), "test-key")

        # Wrong current_api_key.
        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"api_key": "new"}, "current_api_key": "not-the-key"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(get_setting_value(session, "api_key"), "test-key")

        # Correct current_api_key rotates the value without echoing it back.
        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"api_key": "new"}, "current_api_key": "test-key"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(get_setting_value(session, "api_key"), "new")
        self.assertNotIn("new", [entry["value"] for entry in resp.get_json()["updated"]])

    def test_secret_update_and_plain_setting_commit_together(self):
        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={
                "changes": {"api_key": "rotated", "button_box_enabled": True},
                "current_api_key": "test-key",
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(get_setting_value(session, "api_key"), "rotated")
        self.assertEqual(get_setting_value(session, "button_box_enabled"), "true")

    def test_settings_validate_all_before_writing(self):
        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"button_box_enabled": True, "button_select_timeout_sec": "bad"}},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(get_setting_value(session, "button_box_enabled"), "false")

    def test_machine_visual_update_and_order(self):
        resp = self.client.patch(
            "/api/dev_admin/machines/washer1",
            json={"display_name": "Left Washer", "type": "washer", "short_label": "LW", "active_in_kiosk": False},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        session.expire_all()
        machine = session.query(Machine).filter_by(name="washer1").first()
        self.assertEqual(machine.ui_name, "Left Washer")
        self.assertEqual(machine.is_enabled, 0)

        resp = self.client.patch("/api/dev_admin/machine-layout", json={"order": ["dryer1", "washer1"]}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([m["machine_key"] for m in resp.get_json()["machines"]], ["dryer1", "washer1"])

    def test_high_risk_technical_update_requires_confirmation(self):
        resp = self.client.patch(
            "/api/dev_admin/machines/washer1",
            json={"technical": {"shelly_ip": "192.168.1.99"}},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("confirm_high_risk", resp.get_json()["errors"])

        resp = self.client.patch(
            "/api/dev_admin/machines/washer1",
            json={"technical": {"shelly_ip": "192.168.1.99"}, "confirm_high_risk": True},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        session.expire_all()
        self.assertEqual(session.query(Device).filter_by(name="Washer UNI").first().ip, "192.168.1.99")

    def test_duplicate_i4_button_index_rejected(self):
        resp = self.client.patch(
            "/api/dev_admin/machines/washer1",
            json={"technical": {"i4_button_index": 1}, "confirm_high_risk": True},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("technical.i4_button_index", resp.get_json()["errors"])

    def test_export_config_excludes_raw_secrets(self):
        resp = self.client.get("/api/dev_admin/export-config", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        body = str(payload)
        self.assertNotIn("test-key", body)
        self.assertNotIn("secret-token", body)
        self.assertTrue(payload["secret_metadata"]["api_key_is_set"])
        self.assertTrue(payload["secret_metadata"]["reisa_bearer_token_is_set"])

    def test_ui_state_reflects_layout_and_active_in_kiosk(self):
        update_setting_value(session, "machine_card_layout", '{"version":1,"machines":{"dryer1":{"display_order":1,"type":"dryer","short_label":"D1","description":"hot"},"washer1":{"display_order":2,"type":"washer","short_label":"W1","description":"cold"}}}')
        device = DeviceInfo(id=self.dev1.id, name="Washer UNI", role="washer_uni", model="shelly-uni", ip="192.168.1.11", relay_channel=0, input_channel=None, metric_source="none")
        device2 = DeviceInfo(id=self.dev2.id, name="Dryer UNI", role="dryer_uni", model="shelly-uni", ip="192.168.1.12", relay_channel=0, input_channel=None, metric_source="none")
        config = MachineConfigInfo(on_threshold=1, off_threshold=0, on_confirm_ms=0, off_confirm_ms=0, poll_interval_ms=1000)
        store = MachineStateStore.instance()
        store.update_definitions({
            "washer1": MachineRuntime(db_id=self.m1.id, slug="washer1", ui_name="Washer 1", uni_device=device, config=config, i4_device_id=self.i4.id, i4_button_index=0, is_enabled=True, run_state=RUNSTATE_AVAILABLE),
            "dryer1": MachineRuntime(db_id=self.m2.id, slug="dryer1", ui_name="Dryer 1", uni_device=device2, config=config, i4_device_id=self.i4.id, i4_button_index=1, is_enabled=True, run_state=RUNSTATE_AVAILABLE),
        }, {})
        # /api/ui_state is the kiosk API: it authenticates with X-API-KEY, not Basic.
        resp = self.client.get("/api/ui_state", headers={"X-API-KEY": "test-key"})
        self.assertEqual(resp.status_code, 200)
        machines = resp.get_json()["machines"]
        self.assertEqual([m["id"] for m in machines], ["dryer1", "washer1"])
        self.assertEqual(machines[0]["type"], "dryer")
        self.assertEqual(machines[0]["short_label"], "D1")

    # ----- Beta tuning settings -----

    def test_new_tuning_settings_are_exposed_and_editable(self):
        resp = self.client.get("/api/dev_admin/settings", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        settings = {s["key"]: s for g in resp.get_json()["groups"] for s in g["settings"]}
        for key in (
            "selection_notice_seconds",
            "started_notice_seconds",
            "error_notice_seconds",
            "kiosk_poll_interval_ms",
            "relay_pulse_duration_sec",
            "shelly_http_timeout_sec",
            "telemetry_http_timeout_sec",
            "code_expiration_days",
            "reisa_connect_timeout_ms",
            "reisa_retry_worker_enabled",
        ):
            self.assertIn(key, settings, key)
            self.assertTrue(settings[key]["editable"], key)

    def test_kiosk_input_mode_is_read_only(self):
        resp = self.client.get("/api/dev_admin/settings", headers=self.headers)
        settings = {s["key"]: s for g in resp.get_json()["groups"] for s in g["settings"]}
        self.assertIn("kiosk_input_mode", settings)
        self.assertFalse(settings["kiosk_input_mode"]["editable"])

        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"kiosk_input_mode": "touch"}},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)

    def test_tuning_settings_reject_out_of_range_values(self):
        for key, bad_value in (
            ("selection_notice_seconds", 0.1),
            ("started_notice_seconds", 999),
            ("kiosk_poll_interval_ms", 10),
            ("relay_pulse_duration_sec", 60),
            ("shelly_http_timeout_sec", 0),
            ("code_expiration_days", -1),
            ("reisa_retry_worker_batch_size", 0),
        ):
            resp = self.client.patch(
                "/api/dev_admin/settings",
                json={"changes": {key: bad_value}},
                headers=self.headers,
            )
            self.assertEqual(resp.status_code, 400, key)
            self.assertIn(key, resp.get_json()["errors"], key)
            self.assertIsNone(get_setting_value(session, key), key)

    def test_tuning_settings_round_trip(self):
        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"started_notice_seconds": 8, "kiosk_poll_interval_ms": 2000}},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(machine_control.started_notice_seconds(), 8.0)

        resp = self.client.get("/api/ui_state", headers={"X-API-KEY": "test-key"})
        self.assertEqual(resp.get_json()["poll_interval_ms"], 2000)

    def test_reservation_minutes_drives_kiosk_copy(self):
        update_setting_value(session, "machine_reservation_minutes", "25")
        self.assertEqual(machine_control.reservation_minutes(), 25)
        resp = self.client.get("/api/ui_state", headers={"X-API-KEY": "test-key"})
        self.assertEqual(resp.get_json()["reservation_minutes"], 25)

    # ----- Danger zone -----

    def test_disabling_dev_admin_requires_confirmation_phrase(self):
        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"dev_admin_enabled": False}},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["requires_confirmation"], "dev_admin_enabled")
        self.assertEqual(get_setting_value(session, "dev_admin_enabled"), "true")

        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"dev_admin_enabled": False}, "confirmation_phrase": "nope"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(get_setting_value(session, "dev_admin_enabled"), "true")

        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={
                "changes": {"dev_admin_enabled": False},
                "confirmation_phrase": LOCKOUT_CONFIRMATION_PHRASE,
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(get_setting_value(session, "dev_admin_enabled"), "false")

    def test_enabling_dev_admin_needs_no_confirmation(self):
        resp = self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"dev_admin_enabled": True}},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)

    # ----- Audit log -----

    def test_settings_change_is_audited(self):
        self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"button_box_enabled": True}},
            headers=self.headers,
        )
        entries = session.query(SettingsAuditLog).filter_by(entity_key="button_box_enabled").all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].old_value, "false")
        self.assertEqual(entries[0].new_value, "true")
        self.assertEqual(entries[0].source, "dev_admin")

    def test_unchanged_setting_is_not_audited(self):
        self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"button_box_enabled": False}},
            headers=self.headers,
        )
        self.assertEqual(session.query(SettingsAuditLog).count(), 0)

    def test_machine_change_is_audited(self):
        self.client.patch(
            "/api/dev_admin/machines/washer1",
            json={"display_name": "Left Washer"},
            headers=self.headers,
        )
        entry = session.query(SettingsAuditLog).filter_by(entity_key="washer1", field="ui_name").first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.old_value, "Washer 1")
        self.assertEqual(entry.new_value, "Left Washer")

    def test_secret_rotation_is_audited_without_the_value(self):
        resp = self.client.post(
            "/api/dev_admin/generate_api_key",
            json={"current_api_key": "test-key"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        new_key = resp.get_json()["new_api_key"]

        entry = session.query(SettingsAuditLog).filter_by(entity_key="api_key").first()
        self.assertIsNotNone(entry)
        self.assertTrue(entry.is_high_risk)
        self.assertNotIn(new_key, str(entry.new_value))
        self.assertNotIn("test-key", str(entry.old_value))
        self.assertEqual(entry.new_value, "<set>")

    def test_generate_api_key_rejects_wrong_current_key(self):
        resp = self.client.post(
            "/api/dev_admin/generate_api_key",
            json={"current_api_key": "not-the-key"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(get_setting_value(session, "api_key"), "test-key")

        resp = self.client.post("/api/dev_admin/generate_api_key", json={}, headers=self.headers)
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(get_setting_value(session, "api_key"), "test-key")

    # ----- Atomic machine batch save -----

    def test_batch_machine_save_is_all_or_nothing(self):
        resp = self.client.patch(
            "/api/dev_admin/machines",
            json={
                "updates": [
                    {"machine_key": "washer1", "display_name": "Renamed One"},
                    {"machine_key": "dryer1", "display_name": ""},
                ]
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("dryer1", resp.get_json()["errors"])

        # The valid row in the same batch must not have been written.
        machine = session.query(Machine).filter_by(name="washer1").first()
        self.assertNotEqual(machine.ui_name, "Renamed One")

    def test_batch_machine_save_applies_every_change_together(self):
        resp = self.client.patch(
            "/api/dev_admin/machines",
            json={
                "updates": [
                    {"machine_key": "washer1", "display_name": "Left Washer"},
                    {"machine_key": "dryer1", "display_name": "Right Washer"},
                ],
                "order": ["dryer1", "washer1"],
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        session.expire_all()
        names = {m.name: m.ui_name for m in session.query(Machine).all()}
        self.assertEqual(names["washer1"], "Left Washer")
        self.assertEqual(names["dryer1"], "Right Washer")

        payload = resp.get_json()
        order = [m["machine_key"] for m in payload["machines"]]
        self.assertEqual(order[:2], ["dryer1", "washer1"])

    def test_batch_machine_save_rejects_duplicate_i4_index_within_the_batch(self):
        resp = self.client.patch(
            "/api/dev_admin/machines",
            json={
                "updates": [
                    {
                        "machine_key": "washer1",
                        "technical": {"i4_button_index": 5},
                        "confirm_high_risk": True,
                    },
                    {
                        "machine_key": "dryer1",
                        "technical": {"i4_button_index": 5},
                        "confirm_high_risk": True,
                    },
                ]
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        errors = resp.get_json()["errors"]
        self.assertTrue(
            any(
                "i4_button_index" in field
                for fields in errors.values()
                for field in fields
            ),
            msg=f"expected an i4 conflict, got {errors}",
        )
        session.expire_all()
        indexes = [m.i4_button_index for m in session.query(Machine).all()]
        self.assertNotEqual(indexes.count(5), 2)

    def test_batch_machine_save_rejects_unknown_machine_without_writing(self):
        resp = self.client.patch(
            "/api/dev_admin/machines",
            json={
                "updates": [
                    {"machine_key": "washer1", "display_name": "Should Not Persist"},
                    {"machine_key": "does-not-exist", "display_name": "Nope"},
                ]
            },
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        session.expire_all()
        machine = session.query(Machine).filter_by(name="washer1").first()
        self.assertNotEqual(machine.ui_name, "Should Not Persist")

    # ----- Diagnostics -----

    def test_diagnostics_endpoint_returns_scan_logs_metrics_and_audit(self):
        self.client.patch(
            "/api/dev_admin/settings",
            json={"changes": {"button_box_enabled": True}},
            headers=self.headers,
        )
        resp = self.client.get("/api/dev_admin/diagnostics", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertIn("scan_logs", payload)
        self.assertIn("metrics", payload)
        self.assertTrue(any(e["entity_key"] == "button_box_enabled" for e in payload["audit_log"]))

    def test_telemetry_endpoint_exposes_readings_and_thresholds(self):
        device = DeviceInfo(id=self.dev1.id, name="Washer UNI", role="washer_uni", model="shelly-uni", ip="192.168.1.11", relay_channel=0, input_channel=None, metric_source="power")
        config = MachineConfigInfo(on_threshold=8, off_threshold=3, on_confirm_ms=1200, off_confirm_ms=3000, poll_interval_ms=1000)
        store = MachineStateStore.instance()
        store.update_definitions({
            "washer1": MachineRuntime(db_id=self.m1.id, slug="washer1", ui_name="Washer 1", uni_device=device, config=config, i4_device_id=self.i4.id, i4_button_index=0, is_enabled=True, run_state=RUNSTATE_AVAILABLE),
        }, {})
        store.update_measurement("washer1", 12.5, True, 100.0)

        resp = self.client.get("/api/dev_admin/telemetry", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        machines = resp.get_json()["machines"]
        self.assertEqual(len(machines), 1)
        self.assertEqual(machines[0]["last_value"], 12.5)
        self.assertEqual(machines[0]["band"], "high")
        self.assertEqual(machines[0]["config"]["on_threshold"], 8)
        self.assertEqual(machines[0]["config"]["off_threshold"], 3)

    def test_diagnostics_endpoints_respect_the_kill_switch(self):
        update_setting_value(session, "dev_admin_enabled", "false")
        for path in ("/api/dev_admin/telemetry", "/api/dev_admin/diagnostics"):
            resp = self.client.get(path, headers=self.headers)
            self.assertEqual(resp.status_code, 403, path)

    # ----- Remote control -----

    def test_remote_scan_rejects_missing_code(self):
        resp = self.client.post("/api/dev_admin/remote_scan", json={"code": "  "}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)

    def test_remote_touch_select_rejects_missing_machine_id(self):
        resp = self.client.post("/api/dev_admin/remote_touch_select", json={}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)

    def test_remote_touch_select_conflicts_when_no_code_is_armed(self):
        resp = self.client.post(
            "/api/dev_admin/remote_touch_select",
            json={"machine_id": "washer1"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(resp.get_json()["success"])

    def test_remote_reset_returns_kiosk_to_ready(self):
        machine_control.update_ui_state({"state": "choose_machine", "message": "pick one"})
        resp = self.client.post("/api/dev_admin/remote_reset", json={}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(machine_control.UI_STATE["state"], "waiting_for_code")
        self.assertIsNone(machine_control.UI_STATE["current_machine"])


if __name__ == "__main__":
    unittest.main()
