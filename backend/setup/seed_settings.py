"""Utilities for initialising default settings in the database."""

from __future__ import annotations

import hashlib
import logging
import secrets
from typing import Optional

from backend.models import Session, init_db
from backend.models.setting_model import Settings, get_setting_value, update_setting_value




def _ensure_db_initialized() -> None:
    """Initialize database tables before running seed operations."""

    init_db()

DEFAULT_SETTINGS = {
    "admin_username": "admin",
    "admin_password_hash": hashlib.sha256(b"admin").hexdigest(),
    "cors_allowed_origins": "http://localhost",
    "log_level": "INFO",
    "button_select_timeout_sec": "45",
    "kiosk_input_mode": "hardware_buttons",
    "provider_default": "local",
    "provider_reisa_enabled": "false",
    "backend_relay_enabled": "false",
    "telemetry_enabled": "true",
    "reisa_base_url": "",
    "reisa_bearer_token": "",
    "reisa_connect_timeout_ms": "1500",
    "reisa_read_timeout_ms": "2500",
    "reisa_action_start": "WASHING_MACHINE_START",
    "reisa_action_completion": "WASHING_MACHINE_COMPLETE",
    "reisa_retry_worker_enabled": "false",
    "reisa_retry_worker_interval_sec": "30",
    "reisa_retry_worker_batch_size": "20",
    "serial_port": "/dev/ttyACM0",
    "serial_baudrate": "9600",
    "scan_timeout": "1",
}


def seed_settings() -> None:
    """Populate the database with baseline settings if they are missing."""

    _ensure_db_initialized()
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

    _ensure_db_initialized()
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
