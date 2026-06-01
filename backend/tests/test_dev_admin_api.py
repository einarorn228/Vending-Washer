import unittest

from backend.controllers.telemetry import (
    DeviceInfo,
    MachineConfigInfo,
    MachineRuntime,
    MachineStateStore,
    RUNSTATE_AVAILABLE,
)
from backend.flask_server import app
from backend.models import init_db, session
from backend.models.device_model import Device
from backend.models.machine_model import Machine, MachineConfig
from backend.models.setting_model import Settings, get_setting_value, update_setting_value


class DevAdminApiTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(MachineConfig).delete()
        session.query(Machine).delete()
        session.query(Device).delete()
        session.query(Settings).delete()
        session.commit()
        update_setting_value(session, "api_key", "test-key")
        update_setting_value(session, "dev_admin_enabled", "true")
        update_setting_value(session, "button_box_enabled", "false")
        update_setting_value(session, "backend_relay_enabled", "false")
        update_setting_value(session, "telemetry_enabled", "true")
        update_setting_value(session, "api_key", "test-key")
        update_setting_value(session, "admin_password_hash", "secret-hash")
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
        self.headers = {"X-API-KEY": "test-key"}

    def tearDown(self):
        MachineStateStore.instance().update_definitions({}, {})

    def test_kill_switch_returns_403(self):
        update_setting_value(session, "dev_admin_enabled", "false")
        resp = self.client.get("/api/dev_admin/status", headers=self.headers)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(resp.get_json()["disabled"])

    def test_unlock_requires_valid_api_key(self):
        resp = self.client.post("/api/dev_admin/unlock", headers={"X-API-KEY": "wrong"})
        self.assertEqual(resp.status_code, 401)
        resp = self.client.post("/api/dev_admin/unlock", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

    def test_settings_hide_secrets_and_reject_secret_update(self):
        resp = self.client.get("/api/dev_admin/settings", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        settings = {s["key"]: s for g in payload["groups"] for s in g["settings"]}
        self.assertIsNone(settings["api_key"]["value"])
        self.assertTrue(settings["api_key"]["is_set"])
        self.assertIsNone(settings["reisa_bearer_token"]["value"])

        resp = self.client.patch("/api/dev_admin/settings", json={"changes": {"api_key": "new"}}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(get_setting_value(session, "api_key"), "test-key")

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
        resp = self.client.get("/api/ui_state", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        machines = resp.get_json()["machines"]
        self.assertEqual([m["id"] for m in machines], ["dryer1", "washer1"])
        self.assertEqual(machines[0]["type"], "dryer")
        self.assertEqual(machines[0]["short_label"], "D1")


if __name__ == "__main__":
    unittest.main()
