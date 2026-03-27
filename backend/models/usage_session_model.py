"""Durable local timeline for scan/start/commit lifecycle events."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from backend.models import Base


class UsageSession(Base):
    __tablename__ = "usage_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_uid = Column(String, unique=True, nullable=False, index=True)

    provider = Column(String, nullable=False, default="local")
    provider_reference = Column(String)

    identifier_type = Column(String, nullable=False, default="code")
    identifier_value_masked = Column(String)

    machine_id = Column(String)
    scan_source = Column(String)

    state = Column(String, nullable=False, default="scanned")
    requested_quantity = Column(Integer, nullable=False, default=1)
    committed_quantity = Column(Integer, nullable=False, default=0)
    remaining_after_commit = Column(Integer)

    error_code = Column(String)
    error_detail = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
