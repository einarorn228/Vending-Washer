import os
import unittest
import logging
import backend.utils.logger  # configure logger and ensure file exists

# Copy the log path from your logger setup
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "logs", "app.log")
LOG_FILE = os.path.abspath(LOG_FILE)

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
