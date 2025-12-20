import unittest

from backend.controllers import machine_control
from backend.models import session, init_db
from backend.models.code_model import Code
from backend.models.scan_log_model import ScanLog


class ScanLogTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(ScanLog).delete()
        session.query(Code).delete()
        session.commit()
        self.code = Code(code="VALID1", order_id="ORD1", usage_limit=2, current_usage=0)
        session.add(self.code)
        session.commit()
        machine_control.cancel_reset_timer()
        machine_control.update_ui_state(
            {"state": "waiting_for_code", "message": "Scan your code to start"}
        )
        machine_control.disarm_code()

    def tearDown(self):
        machine_control.cancel_reset_timer()
        machine_control.disarm_code()
        session.close()

    def test_scan_events(self):
        success, _, _ = machine_control.handle_scanned_code("VALID1", source="test")
        self.assertTrue(success)
        machine_control.disarm_code()
        machine_control.update_ui_state(
            {"state": "waiting_for_code", "message": "Scan your code to start"}
        )

        machine_control.handle_scanned_code("INVALID", source="test")
        machine_control.update_ui_state(
            {"state": "waiting_for_code", "message": "Scan your code to start"}
        )
        machine_control.handle_scanned_code(None, source="test")

        logs = session.query(ScanLog).order_by(ScanLog.id).all()
        results = [log.result for log in logs]
        self.assertEqual(len(logs), 3)
        self.assertEqual(results[0], "valid")
        self.assertEqual(results[1], "invalid")
        self.assertEqual(results[2], "invalid")
        self.assertIn("missing_code", logs[2].details)


if __name__ == "__main__":
    unittest.main()
