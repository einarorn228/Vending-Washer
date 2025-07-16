import unittest
from unittest.mock import patch

from backend.models import session, init_db
from backend.models.code_model import Code
from backend.models.scan_log_model import ScanLog
from backend.models.setting_model import Settings

# Initialize DB before importing qr_scanner so settings table exists
init_db()
from backend.controllers.qr_scanner import process_qr_code

class ScanLogTests(unittest.TestCase):
    def setUp(self):
        init_db()
        session.query(ScanLog).delete()
        session.query(Code).delete()
        session.commit()
        self.code = Code(code='VALID1', order_id='ORD1', usage_limit=2, current_usage=0)
        session.add(self.code)
        session.commit()

    def tearDown(self):
        session.close()

    def test_scan_events(self):
        with patch('backend.controllers.qr_scanner.send_shelly_on', return_value=True):
            process_qr_code('VALID1')
        process_qr_code('INVALID')
        with patch('backend.controllers.qr_scanner.send_shelly_on', side_effect=Exception('boom')):
            process_qr_code('VALID1')

        logs = session.query(ScanLog).order_by(ScanLog.id).all()
        results = [log.result for log in logs]
        self.assertEqual(len(logs), 3)
        self.assertEqual(results[0], 'success')
        self.assertEqual(results[1], 'invalid')
        self.assertEqual(results[2], 'error')
        self.assertIn('boom', logs[2].details)

if __name__ == '__main__':
    unittest.main()
