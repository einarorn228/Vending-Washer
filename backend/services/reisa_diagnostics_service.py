"""Operator-facing helpers for diagnosing Reisa sync problems."""

from __future__ import annotations

from typing import Any

from backend.services.reisa_audit_service import list_audit_events_for_session
from backend.services.reisa_audit_service import (
    list_failed_reisa_audit_events,
    list_sessions_with_external_sync_failures,
)
from backend.services.reisa_retry_service import list_retry_jobs, list_retry_jobs_for_session
from backend.services.usage_session_service import get_usage_session


def get_reisa_sync_diagnostics(*, limit: int = 100) -> dict[str, list[dict[str, Any]]]:
    """Return compact diagnostic snapshots for failed Reisa sync operations."""

    bounded = max(min(int(limit), 500), 1)
    return {
        "failed_sessions": list_sessions_with_external_sync_failures(limit=bounded),
        "failed_audit_events": list_failed_reisa_audit_events(limit=bounded),
        "retry_jobs": list_retry_jobs(limit=bounded),
    }


def _next_operator_action(*, session_state: str, has_pending_jobs: bool, has_retryable_errors: bool) -> str:
    if has_pending_jobs:
        return "wait_or_run_retry_due"
    if has_retryable_errors:
        return "create_or_review_retry_job"
    if session_state in {"failed", "start_confirmed"}:
        return "review_latest_audit_and_replay"
    if session_state == "completed":
        return "no_action_completed"
    return "investigate_session_context"


def get_reisa_session_diagnostics(*, session_uid: str, limit: int = 100) -> dict[str, Any]:
    bounded = max(min(int(limit), 500), 1)
    session = get_usage_session(session_uid)
    audit_events = list_audit_events_for_session(session_uid=session_uid, limit=bounded)
    retry_jobs = list_retry_jobs_for_session(session_uid=session_uid, limit=bounded)

    retryable_errors = [event for event in audit_events if event.get("result") == "error" and bool(event.get("retryable"))]
    pending_jobs = [
        job for job in retry_jobs if (job.get("status") or "").strip().lower() in {"pending", "retrying"}
    ]
    successful_audits = [event for event in audit_events if event.get("result") == "ok"]

    session_summary = None
    if session:
        session_summary = {
            "session_uid": session.session_uid,
            "provider": session.provider,
            "state": session.state,
            "machine_id": session.machine_id,
            "provider_reference": session.provider_reference,
            "committed_quantity": session.committed_quantity,
            "remaining_after_commit": session.remaining_after_commit,
            "error_code": session.error_code,
            "error_detail": session.error_detail,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }

    likely_next_action = _next_operator_action(
        session_state=(session_summary or {}).get("state", ""),
        has_pending_jobs=bool(pending_jobs),
        has_retryable_errors=bool(retryable_errors),
    )

    return {
        "session": session_summary,
        "audit_events": audit_events,
        "retry_jobs": retry_jobs,
        "recovery_state": {
            "successful_audit_events": len(successful_audits),
            "retryable_errors": len(retryable_errors),
            "pending_retry_jobs": len(pending_jobs),
            "latest_success_audit_id": successful_audits[0]["id"] if successful_audits else None,
        },
        "likely_next_operator_action": likely_next_action,
    }
