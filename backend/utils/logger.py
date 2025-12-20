"""Centralised logging utilities for the backend."""

from __future__ import annotations

import logging
import os
import random
from logging import Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Set

from dotenv import load_dotenv

POLL_ROUTES: Set[str] = {"/api/ui_state"}
SLOW_MS = 300


class RouteFilter(logging.Filter):
    """Filter out successful poll endpoints unless they are slow."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - see class docstring
        if getattr(record, "_force_log", False):
            return True
        if not hasattr(record, "route") or not hasattr(record, "status"):
            return True
        try:
            status_code = int(getattr(record, "status", 0))
        except (TypeError, ValueError):
            status_code = 0
        if status_code >= 400:
            return True
        if getattr(record, "route") in POLL_ROUTES:
            latency = getattr(record, "latency_ms", None)
            if latency and latency > SLOW_MS:
                return True
            return False
        return True


class SlowRequestFilter(logging.Filter):
    """Mark slow requests so downstream filters always log them."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - see class docstring
        latency = getattr(record, "latency_ms", None)
        try:
            latency_value = int(latency) if latency is not None else None
        except (TypeError, ValueError):
            latency_value = None
        if latency_value is not None and latency_value > SLOW_MS:
            setattr(record, "_force_log", True)
        return True


class RedactFilter(logging.Filter):
    """Mask sensitive identifiers that may appear in structured extras."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - see class docstring
        for key in ("code", "qr_code", "api_key"):
            if hasattr(record, key):
                value = getattr(record, key)
                if value:
                    value_str = str(value)
                    masked = f"{value_str[:2]}***{value_str[-2:]}" if len(value_str) > 4 else "***"
                    setattr(record, key, masked)
        return True


class SamplingFilter(logging.Filter):
    """Apply lightweight sampling to high-volume successful requests."""

    SAMPLE_RATE = 0.01

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - see class docstring
        if getattr(record, "_force_log", False):
            return True
        status = getattr(record, "status", None)
        try:
            status_code = int(status) if status is not None else None
        except (TypeError, ValueError):
            status_code = None
        slow = False
        latency = getattr(record, "latency_ms", None)
        try:
            slow = latency is not None and int(latency) > SLOW_MS
        except (TypeError, ValueError):
            slow = False
        if status_code is not None and status_code < 400 and not slow:
            return random.random() < self.SAMPLE_RATE
        return True

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


def _create_rotating_handler(
    path: Path, level: int, *, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5
) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
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

    route_filter = RouteFilter()
    slow_filter = SlowRequestFilter()
    redact_filter = RedactFilter()
    sampling_filter = SamplingFilter()

    file_handler = _create_rotating_handler(
        APP_LOG_FILE, level, max_bytes=10 * 1024 * 1024, backup_count=5
    )
    file_handler.addFilter(redact_filter)
    file_handler.addFilter(slow_filter)
    file_handler.addFilter(route_filter)
    file_handler.addFilter(sampling_filter)

    console_handler = logging.StreamHandler()
    console_level = logging.INFO if level < logging.INFO else level
    console_handler.setLevel(console_level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    console_handler.addFilter(redact_filter)
    console_handler.addFilter(slow_filter)
    console_handler.addFilter(route_filter)
    console_handler.addFilter(sampling_filter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # Dedicated handlers for structured event/error logs.
    events_logger = logging.getLogger("app.events")
    events_logger.setLevel(logging.INFO)
    events_logger.handlers.clear()
    events_handler = _create_rotating_handler(EVENTS_LOG_FILE, logging.INFO)
    events_handler.addFilter(redact_filter)
    events_handler.addFilter(route_filter)
    events_logger.addHandler(events_handler)
    events_logger.propagate = False

    errors_logger = logging.getLogger("app.errors")
    errors_logger.setLevel(logging.ERROR)
    errors_logger.handlers.clear()
    errors_handler = _create_rotating_handler(ERRORS_LOG_FILE, logging.ERROR)
    errors_handler.addFilter(redact_filter)
    errors_handler.addFilter(route_filter)
    errors_logger.addHandler(errors_handler)
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
