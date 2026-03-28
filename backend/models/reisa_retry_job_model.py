"""Durable retry/replay jobs for failed Reisa sync actions."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.models import Base


class ReisaRetryJob(Base):
    __tablename__ = "reisa_retry_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    session_uid = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False, default="reisa", index=True)
    action_type = Column(String, nullable=False, index=True)
    provider_reference = Column(String, index=True)

    request_payload_redacted = Column(Text)

    status = Column(String, nullable=False, default="pending", index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=5)
    next_attempt_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    last_error = Column(String)
    last_status_code = Column(Integer)
    last_attempt_at = Column(DateTime)
    resolved_at = Column(DateTime)
    disabled = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
