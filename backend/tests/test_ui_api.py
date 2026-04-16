import unittest
from unittest.mock import patch

from flask import Flask

from backend.controllers import machine_control
from backend.controllers.ui_api import ui_api
from backend.models import session, init_db
from backend.models.code_model import Code
from backend.models.scan_log_model import ScanLog
from backend.models.setting_model import update_setting_value
from backend.services.start_orchestrator import StartOutcome


class UiApiScanTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(ScanLog).delete()
        session.query(Code).delete()
        session.commit()
        update_setting_value(session, "api_key", "test-key")
        update_setting_value(session, "kiosk_input_mode", "hardware_buttons")
        machine_control.cancel_reset_timer()
        machine_control.update_ui_state(
            {"state": "waiting_for_code", "message": "Scan your code to start"}
        )
        app = Flask(__name__)
        app.register_blueprint(ui_api)
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.headers = {"X-API-KEY": "test-key"}

    def tearDown(self):
        machine_control.cancel_reset_timer()

    def test_scan_busy_returns_409(self):
        machine_control.update_ui_state(
            {"state": "choose_machine", "message": machine_control.SELECT_MACHINE_MESSAGE}
        )
        resp = self.client.post("/scan_code", json={"code": "CODE"}, headers=self.headers)
        self.assertEqual(resp.status_code, 409)
        payload = resp.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["message"], machine_control.SCAN_BUSY_MESSAGE)

    def test_scan_invalid_returns_400(self):
        resp = self.client.post("/scan_code", json={"code": "INVALID"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)
        payload = resp.get_json()
        self.assertFalse(payload["success"])

    def test_scan_missing_returns_400(self):
        resp = self.client.post("/scan_code", json={}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)
        payload = resp.get_json()
        self.assertFalse(payload["success"])

    def test_touch_select_machine_missing_machine_id_returns_400(self):
        resp = self.client.post("/touch_select_machine", json={}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["message"], "Missing machine_id")

    def test_touch_select_machine_invalid_machine_id_returns_400(self):
        resp = self.client.post(
            "/touch_select_machine",
            json={"machine_id": "unknown"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["message"], "Invalid machine_id")

    @patch("backend.controllers.ui_api._machine_exists", return_value=True)
    def test_touch_select_machine_requires_touch_mode(self, _machine_exists_mock):
        machine_control.update_ui_state({"state": "choose_machine"})
        resp = self.client.post(
            "/touch_select_machine",
            json={"machine_id": "washer1"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["message"], "Touch selection is disabled.")

    @patch("backend.controllers.ui_api._machine_exists", return_value=True)
    def test_touch_select_machine_requires_choose_machine_state(self, _machine_exists_mock):
        update_setting_value(session, "kiosk_input_mode", "touch")
        machine_control.update_ui_state({"state": "waiting_for_code"})
        resp = self.client.post(
            "/touch_select_machine",
            json={"machine_id": "washer1"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 409)
        payload = resp.get_json()
        self.assertEqual(payload["message"], "Machine selection is not active.")
        self.assertEqual(payload["state"], "waiting_for_code")

    @patch("backend.controllers.ui_api._machine_exists", return_value=True)
    @patch("backend.controllers.ui_api.start_from_touch")
    def test_touch_select_machine_success(self, start_from_touch_mock, _machine_exists_mock):
        update_setting_value(session, "kiosk_input_mode", "touch")
        machine_control.update_ui_state({"state": "choose_machine"})
        start_from_touch_mock.return_value = StartOutcome(
            success=True,
            message="Washer 1 is powered on.",
            uses_left=2,
        )

        resp = self.client.post(
            "/touch_select_machine",
            json={"machine_id": "washer1"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["uses_left"], 2)
        self.assertIn("state", payload)
        start_from_touch_mock.assert_called_once_with(machine_id="washer1")

    @patch("backend.controllers.ui_api._machine_exists", return_value=True)
    @patch("backend.controllers.ui_api.start_from_touch")
    def test_touch_select_machine_no_armed_scan_returns_409(
        self, start_from_touch_mock, _machine_exists_mock
    ):
        update_setting_value(session, "kiosk_input_mode", "touch")
        machine_control.update_ui_state({"state": "choose_machine"})
        start_from_touch_mock.return_value = StartOutcome(
            success=False,
            message="No valid scan in progress.",
            uses_left=None,
        )

        resp = self.client.post(
            "/touch_select_machine",
            json={"machine_id": "washer1"},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 409)
        payload = resp.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["message"], "No valid scan in progress.")


if __name__ == "__main__":  # pragma: no cover - convenience
    unittest.main()
