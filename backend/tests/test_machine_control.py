import unittest
from unittest.mock import patch

from backend.controllers import machine_control
from backend.models import Session, init_db
from backend.models.scan_log_model import ScanLog


class ScanGateTests(unittest.TestCase):
    def setUp(self):
        self._original_state = machine_control.UI_STATE.copy()
        machine_control.cancel_reset_timer()
        machine_control.update_ui_state(
            {"state": "waiting_for_code", "message": "Scan your code to start"}
        )
        init_db()
        self.db = Session()
        self.db.query(ScanLog).delete()
        self.db.commit()

    def tearDown(self):
        machine_control.cancel_reset_timer()
        machine_control.update_ui_state(self._original_state)
        self.db.close()

    def test_can_accept_scan_only_when_waiting(self):
        self.assertTrue(machine_control.can_accept_scan())
        machine_control.update_ui_state(
            {"state": "choose_machine", "message": machine_control.SELECT_MACHINE_MESSAGE}
        )
        self.assertFalse(machine_control.can_accept_scan())

    def test_handle_scanned_code_rejects_when_not_ready(self):
        machine_control.update_ui_state(
            {"state": "machine_starting", "message": "Testing busy gate"}
        )
        with patch("backend.controllers.machine_control.validate_code") as mock_validate, patch(
            "backend.controllers.machine_control.inc"
        ) as mock_inc:
            success, message, code_info = machine_control.handle_scanned_code(
                "ABCDEFGH", source="test"
            )
        self.assertFalse(success)
        self.assertEqual(message, machine_control.SCAN_BUSY_MESSAGE)
        self.assertIsNone(code_info)
        mock_validate.assert_not_called()
        mock_inc.assert_called()

        latest = self.db.query(ScanLog).order_by(ScanLog.id.desc()).first()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.result, "invalid")
        self.assertIn("busy_state_machine_starting", latest.details)


if __name__ == "__main__":  # pragma: no cover - convenience
    unittest.main()
