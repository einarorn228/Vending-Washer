"""Application wide logging configuration."""

import logging
import logging.handlers
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
os.chmod(LOG_DIR, 0o755)

LOG_FILE = os.path.join(LOG_DIR, "app.log")
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, "a").close()
    os.chmod(LOG_FILE, 0o644)


def configure_logger() -> logging.Logger:
    """Configure and return the root project logger."""

    logger = logging.getLogger("vending_washer")
    if logger.hasHandlers():
        return logger

    level_name = os.getenv("LOG_LEVEL")
    if level_name is None:
        try:
            from models import session
            from models.setting_model import get_setting_value

            level_name = get_setting_value(session, "log_level", default="INFO")
        except Exception:
            level_name = "INFO"

    level = getattr(logging, level_name.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(processName)s - %(threadName)s - %(levelname)s - %(name)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Configure the logger on module import
logger = configure_logger()


__all__ = ["configure_logger", "logger", "LOG_FILE"]


