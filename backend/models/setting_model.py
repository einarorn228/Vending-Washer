from sqlalchemy import Column, String, Integer
from backend.models import Base, Session, session as default_session

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String, unique=True, nullable=False)  # Key for the setting
    value = Column(String, nullable=False)  # Value for the setting


def get_setting_value(session, key, default=None):
    """Helper function to get a setting value by key."""
    setting = session.query(Settings).filter_by(key=key).first()
    return setting.value if setting else default


def update_setting_value(session, key, value):
    """Helper function to update or add a new setting."""
    setting = session.query(Settings).filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = Settings(key=key, value=value)
        session.add(setting)
    session.commit()


def is_backend_relay_enabled(session=default_session) -> bool:
    raw = get_setting_value(session, "backend_relay_enabled", default="false")
    return str(raw).lower() in ("1", "true", "yes")


def is_telemetry_enabled(session=default_session) -> bool:
    """When false, Shelly telemetry HTTP polls are skipped (dev / no-hardware)."""

    raw = get_setting_value(session, "telemetry_enabled", default="true")
    return str(raw).lower() in ("1", "true", "yes", "on")


def ensure_backend_relay_setting_exists(session_factory=Session) -> None:
    """Ensure backend_relay_enabled exists in the DB with a default value."""

    session = session_factory()
    try:
        exists = session.query(Settings).filter_by(key="backend_relay_enabled").first()
        if not exists:
            session.add(Settings(key="backend_relay_enabled", value="false"))
            session.commit()
    finally:
        session.close()
