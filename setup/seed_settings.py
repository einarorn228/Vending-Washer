from models import Session, init_db
from models.setting_model import Settings, update_setting_value
import hashlib

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
    "log_level": "DEBUG",
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
}

def seed_settings():
    session = Session()
    try:
        for key, value in DEFAULT_SETTINGS.items():
            exists = session.query(Settings).filter_by(key=key).first()
            if not exists:
                update_setting_value(session, key, value)
    finally:
        session.close()

if __name__ == "__main__":
    seed_settings()
