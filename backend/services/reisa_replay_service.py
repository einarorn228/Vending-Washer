"""Manual-first replay of failed Reisa sync actions with local idempotency guards."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional

from backend.integrations.reisa_service import ReisaEntitlement, ReisaServiceError
from backend.providers.provider_selector import resolve_provider_by_name
from backend.providers.reisa_provider import ReisaProvider
from backend.services.reisa_audit_service import (
    REQUEST_COMPLETION_STATUS,
    REQUEST_DEDUCT,
    REQUEST_START_STATUS,
    RESULT_ERROR,
    RESULT_OK,
    list_audit_events_for_session,
    record_reisa_audit,
)
from backend.services.reisa_retry_service import (
    ACTION_COMPLETION_STATUS,
    ACTION_DEDUCT,
    ACTION_START_STATUS,
    get_retry_job,
    list_due_retry_job_ids,
    mark_retry_job_failure,
    mark_retry_job_skipped,
    mark_retry_job_success,
    mark_retry_job_resolved_by_audit,
)
from backend.services.start_orchestrator import session_to_entitlement
from backend.services.usage_session_service import (
    STATE_COMPLETED,
    get_usage_session,
    mark_commit_recovered,
    mark_completion_recovered,
)

logger = logging.getLogger(__name__)


@dataclass
class ReplayResult:
    success: bool
    status: str
    message: str


@dataclass
class _StepResult:
    success: bool
    message: str
    retryable: bool = False
    uses_left: Optional[int] = None
    audit_log_id: Optional[int] = None


def _has_successful_action(session_uid: str, request_type: str) -> bool:
    events = list_audit_events_for_session(session_uid=session_uid, request_type=request_type, result=RESULT_OK, limit=1)
    return bool(events)


def _build_reisa_entitlement(session_uid: str) -> Optional[ReisaEntitlement]:
    session = get_usage_session(session_uid)
    if not session:
        return None
    entitlement = session_to_entitlement(session)
    return entitlement if isinstance(entitlement, ReisaEntitlement) else None


def _idempotency_skip_reason(session_uid: str, action_type: str) -> Optional[str]:
    session = get_usage_session(session_uid)
    if not session:
        return "missing_session"

    if (getattr(session, "provider", "") or "").strip().lower() != "reisa":
        return "non_reisa_session"

    state = (getattr(session, "state", "") or "").strip().lower()
    if action_type == ACTION_START_STATUS:
        if _has_successful_action(session_uid, REQUEST_START_STATUS):
            return "start_status_already_synced"
        return None

    if action_type == ACTION_DEDUCT:
        if _has_successful_action(session_uid, REQUEST_DEDUCT):
            return "deduct_already_synced"
        return None

    if action_type == ACTION_COMPLETION_STATUS:
        if _has_successful_action(session_uid, REQUEST_COMPLETION_STATUS):
            return "completion_status_already_synced"
        if state == STATE_COMPLETED and getattr(session, "error_code", None) != "completion_sync_failed":
            return "session_already_completed"
        return None

    return "unsupported_action"


def _replay_start_status(provider: ReisaProvider, *, session_uid: str, uuid: str, provider_reference: str) -> _StepResult:
    try:
        provider.service.post_start_status(uuid, action=provider.action_start)
        audit_id = record_reisa_audit(
            session_uid=session_uid,
            request_type=REQUEST_START_STATUS,
            endpoint=f"/uuid/{uuid}/status",
            method="POST",
            result=RESULT_OK,
            provider_reference=provider_reference,
            request_payload={"action": provider.action_start, "replay": True},
        )
        return _StepResult(True, "start_status synced", audit_log_id=audit_id)
    except ReisaServiceError as exc:
        record_reisa_audit(
            session_uid=session_uid,
            request_type=REQUEST_START_STATUS,
            endpoint=f"/uuid/{uuid}/status",
            method="POST",
            result=RESULT_ERROR,
            provider_reference=provider_reference,
            request_payload={"action": provider.action_start, "replay": True},
            retryable=exc.retryable,
            error_message=exc.message,
        )
        return _StepResult(False, exc.message, retryable=exc.retryable)


def _replay_deduct(provider: ReisaProvider, *, session_uid: str, uuid: str, provider_reference: str) -> _StepResult:
    try:
        deduct = provider.service.deduct_usage(uuid, quantity=1)
        audit_id = record_reisa_audit(
            session_uid=session_uid,
            request_type=REQUEST_DEDUCT,
            endpoint=f"/uuid/{uuid}/deduct",
            method="POST",
            result=RESULT_OK,
            provider_reference=provider_reference,
            request_payload={"quantity": 1, "replay": True},
            response_payload=deduct.raw,
        )
        mark_commit_recovered(
            session_uid,
            committed_quantity=1,
            remaining_after_commit=deduct.uses_left,
        )
        return _StepResult(True, "deduct synced", uses_left=deduct.uses_left, audit_log_id=audit_id)
    except ReisaServiceError as exc:
        record_reisa_audit(
            session_uid=session_uid,
            request_type=REQUEST_DEDUCT,
            endpoint=f"/uuid/{uuid}/deduct",
            method="POST",
            result=RESULT_ERROR,
            provider_reference=provider_reference,
            request_payload={"quantity": 1, "replay": True},
            retryable=exc.retryable,
            error_message=exc.message,
        )
        return _StepResult(False, exc.message, retryable=exc.retryable)


def _replay_completion_status(provider: ReisaProvider, *, session_uid: str, uuid: str, provider_reference: str) -> _StepResult:
    try:
        provider.service.post_completion_status(uuid, action=provider.action_completion)
        audit_id = record_reisa_audit(
            session_uid=session_uid,
            request_type=REQUEST_COMPLETION_STATUS,
            endpoint=f"/uuid/{uuid}/status",
            method="POST",
            result=RESULT_OK,
            provider_reference=provider_reference,
            request_payload={"action": provider.action_completion, "replay": True},
        )
        mark_completion_recovered(session_uid)
        return _StepResult(True, "completion_status synced", audit_log_id=audit_id)
    except ReisaServiceError as exc:
        record_reisa_audit(
            session_uid=session_uid,
            request_type=REQUEST_COMPLETION_STATUS,
            endpoint=f"/uuid/{uuid}/status",
            method="POST",
            result=RESULT_ERROR,
            provider_reference=provider_reference,
            request_payload={"action": provider.action_completion, "replay": True},
            retryable=exc.retryable,
            error_message=exc.message,
        )
        return _StepResult(False, exc.message, retryable=exc.retryable)


def replay_retry_job(job_id: int) -> ReplayResult:
    job = get_retry_job(job_id)
    if not job:
        return ReplayResult(False, "missing", "Retry job not found")

    session_uid = (job.session_uid or "").strip()
    action_type = (job.action_type or "").strip().lower()
    skip_reason = _idempotency_skip_reason(session_uid, action_type)
    if skip_reason:
        mark_retry_job_skipped(job_id, reason=skip_reason)
        return ReplayResult(True, "skipped", skip_reason)

    provider = resolve_provider_by_name("reisa")
    if not isinstance(provider, ReisaProvider):
        mark_retry_job_failure(job_id, error_message="Reisa provider unavailable", retryable=False)
        return ReplayResult(False, "failed", "Reisa provider unavailable")

    entitlement = _build_reisa_entitlement(session_uid)
    if entitlement is None:
        mark_retry_job_skipped(job_id, reason="missing_reisa_entitlement")
        return ReplayResult(True, "skipped", "missing_reisa_entitlement")

    uuid = (entitlement.token or "").strip()
    if not uuid:
        mark_retry_job_skipped(job_id, reason="missing_uuid_token")
        return ReplayResult(True, "skipped", "missing_uuid_token")

    provider_reference = entitlement.token or entitlement.external_id

    try:
        if action_type == ACTION_START_STATUS:
            start_result = _replay_start_status(
                provider,
                session_uid=session_uid,
                uuid=uuid,
                provider_reference=provider_reference,
            )
            if not start_result.success:
                mark_retry_job_failure(job_id, error_message=start_result.message, retryable=start_result.retryable)
                return ReplayResult(False, "failed", start_result.message)
            if start_result.audit_log_id:
                mark_retry_job_resolved_by_audit(job_id, resolved_by_audit_log_id=start_result.audit_log_id)

            # Recovery consistency: successful start replay should not leave pending deduct unsynced.
            if not _has_successful_action(session_uid, REQUEST_DEDUCT):
                deduct_result = _replay_deduct(
                    provider,
                    session_uid=session_uid,
                    uuid=uuid,
                    provider_reference=provider_reference,
                )
                if not deduct_result.success:
                    if deduct_result.retryable:
                        mark_retry_job_success(job_id)
                        if start_result.audit_log_id:
                            mark_retry_job_resolved_by_audit(job_id, resolved_by_audit_log_id=start_result.audit_log_id)
                        return ReplayResult(
                            True,
                            "succeeded",
                            "start_status synced; deduct follow-up retry job queued",
                        )
                    mark_retry_job_failure(job_id, error_message=deduct_result.message, retryable=False)
                    return ReplayResult(False, "failed", f"start_status synced but deduct failed: {deduct_result.message}")

        elif action_type == ACTION_DEDUCT:
            deduct_result = _replay_deduct(
                provider,
                session_uid=session_uid,
                uuid=uuid,
                provider_reference=provider_reference,
            )
            if not deduct_result.success:
                mark_retry_job_failure(job_id, error_message=deduct_result.message, retryable=deduct_result.retryable)
                return ReplayResult(False, "failed", deduct_result.message)
            if deduct_result.audit_log_id:
                mark_retry_job_resolved_by_audit(job_id, resolved_by_audit_log_id=deduct_result.audit_log_id)

        elif action_type == ACTION_COMPLETION_STATUS:
            completion_result = _replay_completion_status(
                provider,
                session_uid=session_uid,
                uuid=uuid,
                provider_reference=provider_reference,
            )
            if not completion_result.success:
                mark_retry_job_failure(job_id, error_message=completion_result.message, retryable=completion_result.retryable)
                return ReplayResult(False, "failed", completion_result.message)
            if completion_result.audit_log_id:
                mark_retry_job_resolved_by_audit(job_id, resolved_by_audit_log_id=completion_result.audit_log_id)
        else:
            mark_retry_job_skipped(job_id, reason="unsupported_action")
            return ReplayResult(True, "skipped", "unsupported_action")

        mark_retry_job_success(job_id)
        return ReplayResult(True, "succeeded", "Replay succeeded")
    except Exception as exc:
        logger.exception("Unexpected replay failure", extra={"job_id": job_id, "action_type": action_type})
        mark_retry_job_failure(job_id, error_message="Unexpected replay failure", retryable=True)
        return ReplayResult(False, "failed", str(exc))


def replay_due_jobs(*, limit: int = 20) -> dict[str, int]:
    ids = list_due_retry_job_ids(limit=limit)
    succeeded = 0
    failed = 0
    skipped = 0
    for job_id in ids:
        result = replay_retry_job(job_id)
        if result.status == "succeeded":
            succeeded += 1
        elif result.status == "skipped":
            skipped += 1
        else:
            failed += 1
    return {
        "processed": len(ids),
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
    }
