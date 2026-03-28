"""Persistence helpers for durable usage-session lifecycle tracking."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Optional
from uuid import uuid4

from backend.models import Session
from backend.models.usage_session_model import UsageSession

logger = logging.getLogger(__name__)

STATE_SCANNED = "scanned"
STATE_AUTHORIZED = "authorized"
STATE_START_REQUESTED = "start_requested"
STATE_START_CONFIRMED = "start_confirmed"
STATE_COMMIT_OK = "commit_ok"
STATE_COMPLETED = "completed"
STATE_FAILED = "failed"
STATE_TIMED_OUT = "timed_out"


def _mask_identifier(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    if len(raw) <= 6:
        return "*" * len(raw)
    return f"{raw[:2]}***{raw[-2:]}"


def _get_session():
    return Session()


def get_usage_session(session_uid: Optional[str]) -> Optional[UsageSession]:
    if not session_uid:
        return None

    db = _get_session()
    try:
        row = db.query(UsageSession).filter_by(session_uid=session_uid).first()
        if not row:
            return None
        db.expunge(row)
        return row
    finally:
        db.close()


def create_usage_session(
    *,
    provider: str,
    provider_reference: Optional[str],
    identifier_type: str,
    identifier_value: Optional[str],
    machine_id: Optional[str],
    scan_source: Optional[str],
    state: str,
    requested_quantity: int = 1,
) -> str:
    session_uid = uuid4().hex
    db = _get_session()
    try:
        row = UsageSession(
            session_uid=session_uid,
            provider=provider,
            provider_reference=provider_reference,
            identifier_type=identifier_type,
            identifier_value_masked=_mask_identifier(identifier_value),
            machine_id=machine_id,
            scan_source=scan_source,
            state=state,
            requested_quantity=max(requested_quantity, 1),
            committed_quantity=0,
        )
        db.add(row)
        db.commit()
        return session_uid
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to create usage session",
            extra={"provider": provider, "state": state, "machine": machine_id},
        )
        raise
    finally:
        db.close()


def update_usage_session(
    session_uid: Optional[str],
    *,
    state: Optional[str] = None,
    machine_id: Optional[str] = None,
    committed_quantity: Optional[int] = None,
    remaining_after_commit: Optional[int] = None,
    error_code: Optional[str] = None,
    error_detail: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
) -> bool:
    if not session_uid:
        return False

    db = _get_session()
    try:
        row = db.query(UsageSession).filter_by(session_uid=session_uid).first()
        if not row:
            return False

        if state is not None:
            row.state = state
        if machine_id is not None:
            row.machine_id = machine_id
        if committed_quantity is not None:
            row.committed_quantity = committed_quantity
        if remaining_after_commit is not None:
            row.remaining_after_commit = remaining_after_commit
        if error_code is not None:
            row.error_code = error_code
        if error_detail is not None:
            row.error_detail = error_detail
        if started_at is not None:
            row.started_at = started_at
        if completed_at is not None:
            row.completed_at = completed_at

        row.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("Failed to update usage session", extra={"session_uid": session_uid})
        return False
    finally:
        db.close()


def mark_committed(
    session_uid: Optional[str],
    *,
    machine_id: Optional[str],
    committed_quantity: int,
    remaining_after_commit: Optional[int],
) -> bool:
    """Mark session as commit_ok once, ignoring duplicate commit attempts safely."""

    if not session_uid:
        return False

    db = _get_session()
    try:
        row = db.query(UsageSession).filter_by(session_uid=session_uid).first()
        if not row:
            return False

        if row.state in {STATE_COMMIT_OK, STATE_COMPLETED}:
            logger.info(
                "Ignoring duplicate commit transition",
                extra={"session_uid": session_uid, "state": row.state},
            )
            return False

        row.state = STATE_COMMIT_OK
        if machine_id is not None:
            row.machine_id = machine_id
        row.committed_quantity = max(committed_quantity, 0)
        row.remaining_after_commit = remaining_after_commit
        row.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("Failed to mark committed", extra={"session_uid": session_uid})
        return False
    finally:
        db.close()


def mark_completed_for_machine(machine_id: Optional[str], *, completed_at: Optional[datetime] = None) -> bool:
    """Mark latest committed/start-confirmed session for machine as completed once."""

    if not machine_id:
        return False

    db = _get_session()
    try:
        row = (
            db.query(UsageSession)
            .filter(
                UsageSession.machine_id == machine_id,
                UsageSession.state.in_([STATE_COMMIT_OK, STATE_START_CONFIRMED, STATE_COMPLETED]),
            )
            .order_by(UsageSession.updated_at.desc(), UsageSession.id.desc())
            .first()
        )
        if not row:
            return False

        if row.state == STATE_COMPLETED or row.completed_at is not None:
            logger.info(
                "Ignoring duplicate completion transition",
                extra={"machine_id": machine_id, "session_uid": row.session_uid},
            )
            return False

        row.state = STATE_COMPLETED
        row.completed_at = completed_at or datetime.utcnow()
        row.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("Failed to mark completed", extra={"machine_id": machine_id})
        return False
    finally:
        db.close()
