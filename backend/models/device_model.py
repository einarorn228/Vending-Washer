"""Device model representing hardware endpoints the application interacts with."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from backend.models import Base


class Device(Base):
    """Database row describing a physical device (Shelly, washer UNI, etc)."""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    model = Column(String)
    ip = Column(String, nullable=False)
    relay_channel = Column(Integer)
    input_channel = Column(Integer)
    metric_source = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

