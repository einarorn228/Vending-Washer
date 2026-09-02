"""Audit records for configuration changes made through the dev/admin panel.

Beta operators tune timings and thresholds live, so behaviour changes need to be
traceable back to the change that caused them. Raw secrets are never recorded --
see ``redact_audit_value``.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.models import Base

ENTITY_SETTING = "setting"
ENTITY_MACHINE = "machine"

SECRET_PLACEHOLDER_SET = "<set>"
SECRET_PLACEHOLDER_UNSET = "<not set>"


class SettingsAuditLog(Base):
    __tablename__ = "settings_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    source = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_key = Column(String, nullable=False, index=True)
    field = Column(String, nullable=False)

    old_value = Column(Text)
    new_value = Column(Text)

    is_high_risk = Column(Boolean, nullable=False, default=False)
    restart_required = Column(Boolean, nullable=False, default=False)


def redact_audit_value(value) -> str:
    """Collapse a secret to presence metadata so it never reaches the audit table."""

    return SECRET_PLACEHOLDER_SET if value not in (None, "") else SECRET_PLACEHOLDER_UNSET


def serialize_audit_entry(entry: SettingsAuditLog) -> dict:
    return {
        "id": entry.id,
        "created_at": entry.created_at.isoformat() + "Z" if entry.created_at else None,
        "source": entry.source,
        "entity_type": entry.entity_type,
        "entity_key": entry.entity_key,
        "field": entry.field,
        "old_value": entry.old_value,
        "new_value": entry.new_value,
        "is_high_risk": bool(entry.is_high_risk),
        "restart_required": bool(entry.restart_required),
    }
