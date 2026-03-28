"""Durable audit and diagnostics helpers for Reisa external sync behavior."""

from __future__ import annotations

from datetime import datetime
import json
import logging
from typing import Any, Optional

from sqlalchemy import desc

from backend.models import Session
from backend.models.reisa_audit_model import ReisaAuditLog
from backend.models.usage_session_model import UsageSession
from backend.services.reisa_failure_taxonomy import classify_reisa_failure
from backend.services.reisa_retry_service import create_retry_job

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = {
    "authorization",
    "bearer",
    "bearer_token",
    "token",
    "api_key",
    "password",
    "pin",
    "pin_code",
}

RESULT_OK = "ok"
RESULT_ERROR = "error"

REQUEST_LOOKUP = "lookup"
REQUEST_START_STATUS = "start_status"
REQUEST_DEDUCT = "deduct"
REQUEST_COMPLETION_STATUS = "completion_status"


RETRYABLE_REQUEST_ACTIONS = {
    REQUEST_START_STATUS,
    REQUEST_DEDUCT,
    REQUEST_COMPLETION_STATUS,
}


_EXTERNAL_SYNC_ERROR_CODES = {
    "commit_failed",
    "commit_exception",
    "completion_sync_failed",
}


def _get_session():
    return Session()


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            if str(key).strip().lower() in SENSITIVE_KEYS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(child)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _safe_json(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return json.dumps(_redact(value), ensure_ascii=False, sort_keys=True)
    except Exception:
        return json.dumps({"value": "[UNSERIALIZABLE]"})


def record_reisa_audit(
    *,
    request_type: str,
    endpoint: str,
    method: str,
    result: str,
    session_uid: Optional[str] = None,
    provider_reference: Optional[str] = None,
    request_payload: Optional[dict[str, Any]] = None,
    response_status_code: Optional[int] = None,
    response_payload: Optional[Any] = None,
    retryable: bool = False,
    error_message: Optional[str] = None,
) -> Optional[int]:
    db = _get_session()
    try:
        row = ReisaAuditLog(
            session_uid=session_uid,
            request_type=request_type,
            endpoint=endpoint,
            method=method,
            provider_reference=provider_reference,
            request_payload_redacted=_safe_json(request_payload),
            response_status_code=response_status_code,
            response_payload_redacted=_safe_json(response_payload),
            result=result,
            retryable=bool(retryable),
            error_message=(error_message or "")[:512] or None,
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
        audit_id = int(row.id)

        if (
            result == RESULT_ERROR
            and bool(retryable)
            and (request_type or "").strip().lower() in RETRYABLE_REQUEST_ACTIONS
            and (session_uid or "").strip()
        ):
            create_retry_job(
                session_uid=session_uid,
                action_type=request_type,
                provider_reference=provider_reference,
                request_payload_redacted=_safe_json(request_payload),
                last_error=error_message,
                last_status_code=response_status_code,
                source_audit_log_id=audit_id,
            )
        return audit_id
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to persist Reisa audit log",
            extra={"request_type": request_type, "session_uid": session_uid},
        )
        return None
    finally:
        db.close()


def list_failed_reisa_audit_events(limit: int = 100) -> list[dict[str, Any]]:
    db = _get_session()
    try:
        rows = (
            db.query(ReisaAuditLog)
            .filter(ReisaAuditLog.result == RESULT_ERROR)
            .order_by(desc(ReisaAuditLog.created_at), desc(ReisaAuditLog.id))
            .limit(max(min(int(limit), 500), 1))
            .all()
        )
        return [
            {
                "id": row.id,
                "session_uid": row.session_uid,
                "request_type": row.request_type,
                "endpoint": row.endpoint,
                "method": row.method,
                "provider_reference": row.provider_reference,
                "status_code": row.response_status_code,
                "retryable": row.retryable,
                "error_message": row.error_message,
                "failure_category": classify_reisa_failure(
                    request_type=row.request_type,
                    status_code=row.response_status_code,
                    error_message=row.error_message,
                    result=row.result,
                    retryable=bool(row.retryable),
                ),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        db.close()


def list_sessions_with_external_sync_failures(limit: int = 100) -> list[dict[str, Any]]:
    db = _get_session()
    try:
        rows = (
            db.query(UsageSession)
            .filter(
                UsageSession.provider == "reisa",
                UsageSession.error_code.in_(_EXTERNAL_SYNC_ERROR_CODES),
            )
            .order_by(desc(UsageSession.updated_at), desc(UsageSession.id))
            .limit(max(min(int(limit), 500), 1))
            .all()
        )
        return [
            {
                "session_uid": row.session_uid,
                "state": row.state,
                "machine_id": row.machine_id,
                "provider_reference": row.provider_reference,
                "error_code": row.error_code,
                "error_detail": row.error_detail,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    finally:
        db.close()


def list_audit_events_for_session(
    *,
    session_uid: str,
    request_type: Optional[str] = None,
    result: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    db = _get_session()
    try:
        q = db.query(ReisaAuditLog).filter(ReisaAuditLog.session_uid == session_uid)
        if request_type:
            q = q.filter(ReisaAuditLog.request_type == request_type)
        if result:
            q = q.filter(ReisaAuditLog.result == result)

        rows = (
            q.order_by(desc(ReisaAuditLog.created_at), desc(ReisaAuditLog.id))
            .limit(max(min(int(limit), 500), 1))
            .all()
        )
        return [
            {
                "id": row.id,
                "session_uid": row.session_uid,
                "request_type": row.request_type,
                "result": row.result,
                "retryable": row.retryable,
                "status_code": row.response_status_code,
                "error_message": row.error_message,
                "failure_category": classify_reisa_failure(
                    request_type=row.request_type,
                    status_code=row.response_status_code,
                    error_message=row.error_message,
                    result=row.result,
                    retryable=bool(row.retryable),
                ),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    finally:
        db.close()
