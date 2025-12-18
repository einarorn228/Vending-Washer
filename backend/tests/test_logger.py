import logging
import os
import unittest

from backend.utils.logger import APP_LOG_FILE, configure_logger


class LoggerTest(unittest.TestCase):
    def setUp(self):
        configure_logger()

    def test_log_file_creation(self):
        logger = logging.getLogger(__name__)
        logger.info("test message")
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "flush"):
                handler.flush()
        self.assertTrue(os.path.exists(APP_LOG_FILE))
        with open(APP_LOG_FILE) as f:
            content = f.read()
        self.assertIn("test message", content)


if __name__ == "__main__":  # pragma: no cover - convenience
    unittest.main()
