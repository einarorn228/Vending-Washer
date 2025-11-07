"""Centralised logging utilities for the backend."""

from __future__ import annotations

import logging
import os
from logging import Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
APP_LOG_FILE = LOG_DIR / "app.log"
EVENTS_LOG_FILE = LOG_DIR / "events.log"
ERRORS_LOG_FILE = LOG_DIR / "errors.log"

_CONFIGURED_FLAG = "_vending_washer_logger_configured"


def _ensure_log_targets() -> None:
    """Create the log directory and files with permissive defaults."""

    LOG_DIR.mkdir(mode=0o755, parents=True, exist_ok=True)
    try:
        os.chmod(LOG_DIR, 0o755)
    except OSError:
        pass

    for log_file in (APP_LOG_FILE, EVENTS_LOG_FILE, ERRORS_LOG_FILE):
        if not log_file.exists():
            log_file.touch()
            try:
                os.chmod(log_file, 0o644)
            except OSError:
                # Not all platforms support chmod (e.g. Windows containers).
                pass


def _resolve_log_level() -> str:
    """Determine the log level from the environment or settings DB."""

    env_level = os.getenv("LOG_LEVEL")
    if env_level:
        return env_level.upper()

    try:
        from ..models import session
        from ..models.setting_model import get_setting_value

        level = get_setting_value(session, "log_level", default="INFO")
        if level:
            return str(level).upper()
    except Exception:
        # The database may not be initialised on the very first run. Fall back
        # to a sensible default and allow configuration to continue.
        pass

    return "INFO"


def _create_rotating_handler(path: Path, level: int) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s "
            "(%(filename)s:%(lineno)d)"
        )
    )
    return handler


def configure_logger() -> Logger:
    """Configure the root logger with rotating file handlers and console output."""

    load_dotenv()
    _ensure_log_targets()

    root = logging.getLogger()
    if getattr(root, _CONFIGURED_FLAG, False):
        return root

    level_name = _resolve_log_level()
    level = getattr(logging, level_name, logging.INFO)
    if not isinstance(level, int):
        level = logging.INFO
    resolved_level_name = logging.getLevelName(level)
    root.setLevel(level)

    file_handler = _create_rotating_handler(APP_LOG_FILE, level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s "
            "(%(filename)s:%(lineno)d)"
        )
    )

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Dedicated handlers for structured event/error logs.
    events_logger = logging.getLogger("app.events")
    events_logger.setLevel(logging.INFO)
    events_logger.handlers.clear()
    events_logger.addHandler(_create_rotating_handler(EVENTS_LOG_FILE, logging.INFO))
    events_logger.propagate = False

    errors_logger = logging.getLogger("app.errors")
    errors_logger.setLevel(logging.ERROR)
    errors_logger.handlers.clear()
    errors_logger.addHandler(
        _create_rotating_handler(ERRORS_LOG_FILE, logging.ERROR)
    )
    errors_logger.propagate = False

    # Noise reduction from verbose dependencies.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    root.info("Logger configured (level=%s)", resolved_level_name)
    setattr(root, _CONFIGURED_FLAG, True)
    return root


def get_event_logger() -> Logger:
    """Return the dedicated event logger."""

    return logging.getLogger("app.events")


def get_error_logger() -> Logger:
    """Return the dedicated error logger."""

    return logging.getLogger("app.errors")


__all__ = [
    "configure_logger",
    "get_event_logger",
    "get_error_logger",
    "APP_LOG_FILE",
    "EVENTS_LOG_FILE",
    "ERRORS_LOG_FILE",
]
