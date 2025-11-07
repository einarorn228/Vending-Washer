"""Utilities for initialising default settings in the database."""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Optional

from backend.models import Session, init_db
from backend.models.setting_model import Settings, get_setting_value, update_setting_value

init_db()

DEFAULT_SETTINGS = {
    "serial_port": "/dev/ttyUSB0",
    "serial_baudrate": "9600",
    "notification_email": "einarorn864@gmail.com",
    "admin_username": "admin",
    "admin_password_hash": hashlib.sha256(b"admin").hexdigest(),
    "api_rate_limit": "60",
    "ui_refresh_interval": "5",
    "max_machines": "10",
    "machine_types": "washer,dryer",
    "default_machine_type": "washer",
    "max_retry_attempts": "3",
    "log_level": "INFO",
    "shelly_ip": "0",
    "pulse_duration": "1",
    "usage_limit_default": "1",
    # Codes do not expire while unused by default
    "code_expiration_days": "0",
    # How long to keep expired/used codes before deletion
    "expired_code_cleanup_days": "30",
    "scan_timeout": "1",
    "max_usage_limit": "3",
    "cleanup_interval": "7",
    "relay_mode": "on",  # Options: "on", "pulse"
    "cors_allowed_origins": "http://localhost",
}


def seed_settings() -> None:
    """Populate the database with baseline settings if they are missing."""

    session = Session()
    try:
        for key, value in DEFAULT_SETTINGS.items():
            exists = session.query(Settings).filter_by(key=key).first()
            if not exists:
                update_setting_value(session, key, value)
    finally:
        session.close()


def ensure_core_settings(logger: Optional[logging.Logger] = None) -> None:
    """Ensure that critical settings (log level, API key) are present."""

    session = Session()
    created_api_key: Optional[str] = None
    try:
        if get_setting_value(session, "log_level") is None:
            update_setting_value(session, "log_level", "INFO")

        if get_setting_value(session, "api_key") is None:
            created_api_key = secrets.token_hex(32)
            update_setting_value(session, "api_key", created_api_key)
    finally:
        session.close()

    if created_api_key:
        log = logger or logging.getLogger(__name__)
        log.warning(
            "First-run: generated API_KEY=%s. Store it securely.",
            created_api_key,
        )


def bootstrap_settings(logger: Optional[logging.Logger] = None) -> None:
    """Run the complete bootstrap process for application settings."""

    seed_settings()
    ensure_core_settings(logger=logger)


if __name__ == "__main__":
    bootstrap_settings()
