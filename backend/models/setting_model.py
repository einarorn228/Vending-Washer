from sqlalchemy import Column, String, Integer
from . import Base


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
