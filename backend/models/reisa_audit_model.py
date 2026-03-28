"""Durable audit records for Reisa external API interactions."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.models import Base


class ReisaAuditLog(Base):
    __tablename__ = "reisa_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_uid = Column(String, index=True)

    request_type = Column(String, nullable=False, index=True)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    provider_reference = Column(String, index=True)

    request_payload_redacted = Column(Text)
    response_status_code = Column(Integer)
    response_payload_redacted = Column(Text)

    result = Column(String, nullable=False, index=True)
    retryable = Column(Boolean, nullable=False, default=False)
    error_message = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
