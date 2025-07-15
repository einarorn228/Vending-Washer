"""Application wide logging configuration."""

import logging
import logging.handlers
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
try:
    os.chmod(LOG_DIR, 0o755)
except Exception:
    pass  # Some systems may not support chmod (e.g., Windows)

LOG_FILE = os.path.join(LOG_DIR, "app.log")
if not os.path.exists(LOG_FILE):
    open(LOG_FILE, "a").close()
    try:
        os.chmod(LOG_FILE, 0o644)
    except Exception:
        pass


def configure_logger():
    """
    Configures the ROOT logger so ALL logs from ALL modules appear in the log file and console.
    Should be called ONCE at the very top of your entrypoint.
    """
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        return root_logger  # Already configured

    # Get log level from env var or settings DB
    level_name = os.getenv("LOG_LEVEL")
    if level_name is None:
        try:
            from ..models import session
            from ..models.setting_model import get_setting_value

            level_name = get_setting_value(session, "log_level", default="INFO")
        except Exception:
            level_name = "INFO"
    level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s - %(processName)s - %(threadName)s - %(levelname)s - %(name)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    return root_logger


# Call this ONCE at import. All modules should use logging.getLogger(__name__)
configure_logger()

__all__ = ["configure_logger", "LOG_FILE"]
