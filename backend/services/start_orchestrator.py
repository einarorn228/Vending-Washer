"""Start-flow orchestration entrypoints.

Phase 2 introduces provider-backed local entitlement authority while
preserving existing machine-control runtime behavior.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from backend.controllers.machine_control import (
    SCAN_BUSY_MESSAGE,
    ValidatedCode,
    consume_pending_start,
    disarm_code,
    finalize_started_machine,
    get_button_start_code,
    handle_scanned_code,
    resolve_button_machine,
    show_error_state,
    start_machine,
)
from backend.providers.base_provider import BaseProvider
from backend.providers.local_provider import LocalProvider
from backend.services.usage_session_service import (
    STATE_AUTHORIZED,
    STATE_COMMIT_OK,
    STATE_FAILED,
    STATE_SCANNED,
    STATE_START_CONFIRMED,
    STATE_START_REQUESTED,
    create_usage_session,
    update_usage_session,
)

logger = logging.getLogger(__name__)

_provider: BaseProvider = LocalProvider()
_scan_session_lock = threading.Lock()
_scan_sessions: dict[str, str] = {}


@dataclass
class ScanOutcome:
    success: bool
    message: str
    code_info: Optional[ValidatedCode]


@dataclass
class StartOutcome:
    success: bool
    message: str
    uses_left: Optional[int]


def _resolve_or_create_session_uid(
    code_info: ValidatedCode,
    *,
    machine_id: Optional[str],
    scan_source: Optional[str],
) -> str:
    with _scan_session_lock:
        existing = _scan_sessions.pop(code_info.code, None)
    if existing:
        update_usage_session(existing, machine_id=machine_id)
        return existing
    return create_usage_session(
        provider="local",
        provider_reference=code_info.order_id or code_info.code,
        identifier_type="code",
        identifier_value=code_info.code,
        machine_id=machine_id,
        scan_source=scan_source,
        state=STATE_SCANNED,
        requested_quantity=1,
    )


def ingest_scan(raw_code: Optional[str], source: str) -> ScanOutcome:
    """Shared scanner/API ingress orchestration."""

    success, message, code_info = handle_scanned_code(raw_code, source=source)
    if success and code_info:
        session_uid = create_usage_session(
            provider="local",
            provider_reference=code_info.order_id or code_info.code,
            identifier_type="code",
            identifier_value=code_info.code,
            machine_id=None,
            scan_source=source,
            state=STATE_SCANNED,
            requested_quantity=1,
        )
        with _scan_session_lock:
            _scan_sessions[code_info.code] = session_uid
    return ScanOutcome(success=success, message=message, code_info=code_info)


def start_from_code(machine_id: Optional[str], raw_code: Optional[str]) -> StartOutcome:
    """Start flow used by API/manual paths that provide code + machine."""

    code = (raw_code or "").strip()
    if not code or not machine_id:
        return StartOutcome(success=False, message="Missing data", uses_left=None)

    lookup = _provider.lookup(code, mode="local_code")
    if not lookup.success:
        show_error_state(lookup.message)
        return StartOutcome(success=False, message=lookup.message, uses_left=None)

    auth = _provider.authorize(lookup.entitlement, machine_id=machine_id)
    if not auth.authorized or not auth.entitlement:
        show_error_state(auth.message)
        return StartOutcome(success=False, message=auth.message, uses_left=None)

    code_info = auth.entitlement
    session_uid = _resolve_or_create_session_uid(
        code_info, machine_id=machine_id, scan_source="api"
    )
    update_usage_session(session_uid, state=STATE_AUTHORIZED, machine_id=machine_id)
    ok, message = start_machine(code_info, machine_id, session_uid=session_uid)
    if not ok:
        update_usage_session(
            session_uid,
            state=STATE_FAILED,
            error_code="start_rejected",
            error_detail=message,
        )
        show_error_state(message)
        return StartOutcome(success=False, message=message, uses_left=None)

    update_usage_session(session_uid, state=STATE_START_REQUESTED, machine_id=machine_id)
    uses_left = code_info.usage_limit - code_info.current_usage
    return StartOutcome(success=True, message=message, uses_left=uses_left)


def start_from_button(button_index: int) -> StartOutcome:
    """Start flow for i4 button callbacks."""

    machine_id = resolve_button_machine(button_index)
    if not machine_id:
        return StartOutcome(success=False, message="Unknown button.", uses_left=None)

    code_info = get_button_start_code(machine_id)
    if not code_info:
        return StartOutcome(
            success=False,
            message="No valid scan in progress.",
            uses_left=None,
        )

    auth = _provider.authorize(code_info, machine_id=machine_id)
    if not auth.authorized or not auth.entitlement:
        disarm_code()
        return StartOutcome(success=False, message=auth.message, uses_left=None)

    refreshed_code = auth.entitlement
    session_uid = _resolve_or_create_session_uid(
        refreshed_code,
        machine_id=machine_id,
        scan_source="button",
    )
    update_usage_session(session_uid, state=STATE_AUTHORIZED, machine_id=machine_id)
    ok, message = start_machine(refreshed_code, machine_id, session_uid=session_uid)
    uses_left = refreshed_code.usage_limit - refreshed_code.current_usage if ok else None
    if not ok:
        update_usage_session(
            session_uid,
            state=STATE_FAILED,
            error_code="start_rejected",
            error_detail=message,
        )
        show_error_state(message)
    else:
        update_usage_session(session_uid, state=STATE_START_REQUESTED, machine_id=machine_id)
    return StartOutcome(success=ok, message=message, uses_left=uses_left)


def handle_start_confirmed(machine_id: str) -> None:
    """Continue start flow after telemetry confirms machine runstate."""

    pending = consume_pending_start(machine_id)
    if not pending:
        return
    if pending.session_uid:
        update_usage_session(
            pending.session_uid,
            state=STATE_START_CONFIRMED,
            machine_id=machine_id,
            started_at=datetime.utcnow(),
        )
    try:
        commit = _provider.commit_start(pending.code, quantity=1)
        if not commit.success:
            logger.error(
                "Provider commit failed",
                extra={"machine": machine_id, "message": commit.message},
            )
            update_usage_session(
                pending.session_uid,
                state=STATE_FAILED,
                error_code="commit_failed",
                error_detail=commit.message,
            )
            show_error_state("Machine did not start. Please try again.")
            return
        uses_left = commit.uses_left
        if uses_left is None:
            uses_left = max(pending.code.usage_limit - pending.code.current_usage - 1, 0)
        update_usage_session(
            pending.session_uid,
            state=STATE_COMMIT_OK,
            committed_quantity=1,
            remaining_after_commit=uses_left,
        )
        finalize_started_machine(machine_id, pending.code, uses_left)
    except Exception:
        logger.exception("Failed to finalize start", extra={"machine": machine_id})
        update_usage_session(
            pending.session_uid,
            state=STATE_FAILED,
            error_code="commit_exception",
            error_detail="Exception while finalizing start commit",
        )
        show_error_state("Machine did not start. Please try again.")


__all__ = [
    "SCAN_BUSY_MESSAGE",
    "ScanOutcome",
    "StartOutcome",
    "handle_start_confirmed",
    "ingest_scan",
    "start_from_button",
    "start_from_code",
]
