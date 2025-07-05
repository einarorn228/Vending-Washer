import os
import unittest
import logging

logger = logging.getLogger(__name__)


class LoggerTest(unittest.TestCase):
    def test_log_file_creation(self):
        logger.info("test message")
        self.assertTrue(os.path.exists(LOG_FILE))
        with open(LOG_FILE) as f:
            content = f.read()
        self.assertIn("test message", content)

if __name__ == '__main__':
    unittest.main()
