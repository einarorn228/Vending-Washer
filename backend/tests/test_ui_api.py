import unittest

from flask import Flask

from backend.controllers import machine_control
from backend.controllers.ui_api import ui_api
from backend.models import session, init_db
from backend.models.code_model import Code
from backend.models.scan_log_model import ScanLog
from backend.models.setting_model import update_setting_value


class UiApiScanTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(ScanLog).delete()
        session.query(Code).delete()
        session.commit()
        update_setting_value(session, "api_key", "test-key")
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


if __name__ == "__main__":  # pragma: no cover - convenience
    unittest.main()
