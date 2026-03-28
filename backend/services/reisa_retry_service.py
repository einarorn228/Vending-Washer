"""Durable queue helpers for Reisa retry/replay jobs."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any, Optional

from sqlalchemy import and_, asc

from backend.models import Session
from backend.models.reisa_retry_job_model import ReisaRetryJob

logger = logging.getLogger(__name__)

ACTION_START_STATUS = "start_status"
ACTION_DEDUCT = "deduct"
ACTION_COMPLETION_STATUS = "completion_status"

STATUS_PENDING = "pending"
STATUS_RETRYING = "retrying"
STATUS_SUCCEEDED = "succeeded"
STATUS_EXHAUSTED = "exhausted"
STATUS_SKIPPED = "skipped"

RETRYABLE_ACTIONS = {ACTION_START_STATUS, ACTION_DEDUCT, ACTION_COMPLETION_STATUS}


def _get_session():
    return Session()


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(min(parsed, maximum), minimum)


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.utcnow()


def _backoff_seconds(retry_count: int) -> int:
    # Practical bounded backoff: 30s, 60s, 120s, ... capped at 15m.
    base = 30 * (2 ** max(retry_count - 1, 0))
    return min(base, 900)


def create_retry_job(
    *,
    session_uid: str,
    action_type: str,
    provider_reference: Optional[str] = None,
    request_payload_redacted: Optional[str] = None,
    last_error: Optional[str] = None,
    last_status_code: Optional[int] = None,
    max_retries: int = 5,
) -> Optional[int]:
    """Create or refresh a pending retry job for a specific failed Reisa action."""

    normalized_action = (action_type or "").strip().lower()
    normalized_session = (session_uid or "").strip()
    if not normalized_session or normalized_action not in RETRYABLE_ACTIONS:
        return None

    db = _get_session()
    try:
        existing = (
            db.query(ReisaRetryJob)
            .filter(
                ReisaRetryJob.session_uid == normalized_session,
                ReisaRetryJob.action_type == normalized_action,
                ReisaRetryJob.provider == "reisa",
                ReisaRetryJob.disabled.is_(False),
                ReisaRetryJob.status.in_([STATUS_PENDING, STATUS_RETRYING]),
            )
            .order_by(ReisaRetryJob.id.desc())
            .first()
        )
        if existing:
            existing.provider_reference = provider_reference or existing.provider_reference
            existing.request_payload_redacted = request_payload_redacted or existing.request_payload_redacted
            existing.last_error = (last_error or existing.last_error or "")[:512] or None
            existing.last_status_code = last_status_code if last_status_code is not None else existing.last_status_code
            existing.next_attempt_at = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            db.commit()
            return existing.id

        row = ReisaRetryJob(
            session_uid=normalized_session,
            provider="reisa",
            action_type=normalized_action,
            provider_reference=provider_reference,
            request_payload_redacted=request_payload_redacted,
            status=STATUS_PENDING,
            retry_count=0,
            max_retries=_bounded_int(max_retries, default=5, minimum=1, maximum=20),
            next_attempt_at=datetime.utcnow(),
            last_error=(last_error or "")[:512] or None,
            last_status_code=last_status_code,
            disabled=False,
        )
        db.add(row)
        db.commit()
        return row.id
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to create Reisa retry job",
            extra={"session_uid": normalized_session, "action_type": normalized_action},
        )
        return None
    finally:
        db.close()


def mark_retry_job_success(job_id: int) -> bool:
    db = _get_session()
    try:
        row = db.query(ReisaRetryJob).filter_by(id=job_id).first()
        if not row:
            return False
        now = datetime.utcnow()
        row.status = STATUS_SUCCEEDED
        row.last_attempt_at = now
        row.resolved_at = now
        row.updated_at = now
        row.last_error = None
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("Failed to mark retry job success", extra={"job_id": job_id})
        return False
    finally:
        db.close()


def mark_retry_job_skipped(job_id: int, *, reason: str) -> bool:
    db = _get_session()
    try:
        row = db.query(ReisaRetryJob).filter_by(id=job_id).first()
        if not row:
            return False
        now = datetime.utcnow()
        row.status = STATUS_SKIPPED
        row.last_error = (reason or "skipped")[:512]
        row.last_attempt_at = now
        row.resolved_at = now
        row.updated_at = now
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("Failed to mark retry job skipped", extra={"job_id": job_id})
        return False
    finally:
        db.close()


def mark_retry_job_failure(
    job_id: int,
    *,
    error_message: str,
    status_code: Optional[int] = None,
    retryable: bool = True,
) -> bool:
    db = _get_session()
    try:
        row = db.query(ReisaRetryJob).filter_by(id=job_id).first()
        if not row:
            return False

        now = datetime.utcnow()
        row.retry_count = int(row.retry_count or 0) + 1
        row.last_attempt_at = now
        row.last_error = (error_message or "retry failed")[:512]
        row.last_status_code = status_code

        exhausted = (not retryable) or row.retry_count >= max(int(row.max_retries or 1), 1)
        if exhausted:
            row.status = STATUS_EXHAUSTED
            row.resolved_at = now
        else:
            row.status = STATUS_PENDING
            row.next_attempt_at = now + timedelta(seconds=_backoff_seconds(row.retry_count))
        row.updated_at = now

        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("Failed to mark retry job failure", extra={"job_id": job_id})
        return False
    finally:
        db.close()


def get_retry_job(job_id: int) -> Optional[ReisaRetryJob]:
    db = _get_session()
    try:
        row = db.query(ReisaRetryJob).filter_by(id=job_id).first()
        if not row:
            return None
        db.expunge(row)
        return row
    finally:
        db.close()


def list_retry_jobs(
    *,
    limit: int = 100,
    status: Optional[str] = None,
    due_only: bool = False,
) -> list[dict[str, Any]]:
    db = _get_session()
    try:
        q = db.query(ReisaRetryJob).filter(ReisaRetryJob.disabled.is_(False))
        if status:
            q = q.filter(ReisaRetryJob.status == status)
        if due_only:
            q = q.filter(
                and_(
                    ReisaRetryJob.status.in_([STATUS_PENDING, STATUS_RETRYING]),
                    ReisaRetryJob.next_attempt_at <= datetime.utcnow(),
                )
            )

        rows = (
            q.order_by(asc(ReisaRetryJob.next_attempt_at), asc(ReisaRetryJob.id))
            .limit(_bounded_int(limit, default=100, minimum=1, maximum=500))
            .all()
        )
        return [
            {
                "id": row.id,
                "session_uid": row.session_uid,
                "provider": row.provider,
                "action_type": row.action_type,
                "provider_reference": row.provider_reference,
                "status": row.status,
                "retry_count": row.retry_count,
                "max_retries": row.max_retries,
                "next_attempt_at": row.next_attempt_at.isoformat() if row.next_attempt_at else None,
                "last_attempt_at": row.last_attempt_at.isoformat() if row.last_attempt_at else None,
                "last_error": row.last_error,
                "last_status_code": row.last_status_code,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            }
            for row in rows
        ]
    finally:
        db.close()


def list_due_retry_job_ids(*, limit: int = 50) -> list[int]:
    db = _get_session()
    try:
        rows = (
            db.query(ReisaRetryJob.id)
            .filter(
                ReisaRetryJob.disabled.is_(False),
                ReisaRetryJob.status.in_([STATUS_PENDING, STATUS_RETRYING]),
                ReisaRetryJob.next_attempt_at <= _coerce_datetime(None),
            )
            .order_by(asc(ReisaRetryJob.next_attempt_at), asc(ReisaRetryJob.id))
            .limit(_bounded_int(limit, default=50, minimum=1, maximum=200))
            .all()
        )
        return [int(row[0]) for row in rows]
    finally:
        db.close()
