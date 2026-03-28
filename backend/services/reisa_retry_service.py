"""Durable queue helpers for Reisa retry/replay jobs."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import json
import threading
import time
from typing import Any, Optional

from sqlalchemy import and_, asc

from backend.models import Session
from backend.models.setting_model import get_setting_value
from backend.models.reisa_retry_job_model import ReisaRetryJob
from backend.services.reisa_failure_taxonomy import classify_reisa_failure

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


def _load_json(value: Optional[str]) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _to_json(value: dict[str, Any]) -> Optional[str]:
    if not value:
        return None
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return None


def _merge_correlation_payload(
    base_payload: Optional[str],
    *,
    source_audit_log_id: Optional[int] = None,
    resolved_by_audit_log_id: Optional[int] = None,
) -> Optional[str]:
    payload = _load_json(base_payload)
    correlation = payload.get("_correlation")
    if not isinstance(correlation, dict):
        correlation = {}

    if source_audit_log_id is not None:
        correlation["source_audit_log_id"] = int(source_audit_log_id)
    if resolved_by_audit_log_id is not None:
        correlation["resolved_by_audit_log_id"] = int(resolved_by_audit_log_id)

    if correlation:
        payload["_correlation"] = correlation

    return _to_json(payload)


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
    source_audit_log_id: Optional[int] = None,
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
            existing.request_payload_redacted = _merge_correlation_payload(
                request_payload_redacted or existing.request_payload_redacted,
                source_audit_log_id=source_audit_log_id,
            )
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
            request_payload_redacted=_merge_correlation_payload(
                request_payload_redacted,
                source_audit_log_id=source_audit_log_id,
            ),
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


def mark_retry_job_resolved_by_audit(job_id: int, *, resolved_by_audit_log_id: int) -> bool:
    db = _get_session()
    try:
        row = db.query(ReisaRetryJob).filter_by(id=job_id).first()
        if not row:
            return False
        row.request_payload_redacted = _merge_correlation_payload(
            row.request_payload_redacted,
            resolved_by_audit_log_id=resolved_by_audit_log_id,
        )
        row.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("Failed to mark retry job resolution correlation", extra={"job_id": job_id})
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
                **{
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
                    "failure_category": classify_reisa_failure(
                        request_type=row.action_type,
                        status_code=row.last_status_code,
                        error_message=row.last_error,
                        result="error" if row.last_error else "ok",
                        retryable=row.status in {STATUS_PENDING, STATUS_RETRYING},
                    ),
                    "correlation": _load_json(row.request_payload_redacted).get("_correlation"),
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
                }
            }
            for row in rows
        ]
    finally:
        db.close()


def list_retry_jobs_for_session(*, session_uid: str, limit: int = 100) -> list[dict[str, Any]]:
    normalized = (session_uid or "").strip()
    if not normalized:
        return []
    db = _get_session()
    try:
        rows = (
            db.query(ReisaRetryJob)
            .filter(ReisaRetryJob.session_uid == normalized, ReisaRetryJob.disabled.is_(False))
            .order_by(asc(ReisaRetryJob.next_attempt_at), asc(ReisaRetryJob.id))
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
                "failure_category": classify_reisa_failure(
                    request_type=row.action_type,
                    status_code=row.last_status_code,
                    error_message=row.last_error,
                    result="error" if row.last_error else "ok",
                    retryable=row.status in {STATUS_PENDING, STATUS_RETRYING},
                ),
                "correlation": _load_json(row.request_payload_redacted).get("_correlation"),
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


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _worker_settings() -> tuple[bool, int, int]:
    db = _get_session()
    try:
        enabled = _as_bool(get_setting_value(db, "reisa_retry_worker_enabled", "false"))
        interval = _bounded_int(get_setting_value(db, "reisa_retry_worker_interval_sec", "30"), default=30, minimum=5, maximum=300)
        batch_size = _bounded_int(get_setting_value(db, "reisa_retry_worker_batch_size", "20"), default=20, minimum=1, maximum=100)
        return enabled, interval, batch_size
    finally:
        db.close()


def run_retry_worker_loop(*, stop_event: Optional[threading.Event] = None) -> None:
    """Optional safe auto-replay loop. Disabled by default via settings."""

    while True:
        if stop_event and stop_event.is_set():
            return
        try:
            enabled, interval_sec, batch_size = _worker_settings()
            if enabled:
                from backend.services.reisa_replay_service import replay_due_jobs

                summary = replay_due_jobs(limit=batch_size)
                logger.info("Reisa retry worker cycle complete", extra={"summary": summary, "batch_size": batch_size})
        except Exception:
            logger.exception("Reisa retry worker loop failure")

        # Respect the configured interval even while disabled to avoid a hot loop.
        _, interval_sec, _ = _worker_settings()
        time.sleep(interval_sec)
