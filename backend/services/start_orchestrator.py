"""Start-flow orchestration entrypoints with provider selection support."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from backend.controllers.machine_control import (
    SCAN_BUSY_MESSAGE,
    SELECT_MACHINE_MESSAGE,
    ValidatedCode,
    arm_code,
    consume_pending_start,
    disarm_code,
    finalize_started_machine,
    get_button_start_code,
    get_machine_snapshot,
    handle_scanned_code,
    require_ready_to_scan,
    resolve_button_machine,
    show_error_state,
    start_machine,
    update_ui_state,
    write_scan_log,
)
from backend.providers.base_provider import BaseProvider
from backend.providers.provider_selector import resolve_provider
from backend.services.usage_session_service import (
    STATE_AUTHORIZED,
    STATE_FAILED,
    STATE_SCANNED,
    STATE_START_CONFIRMED,
    STATE_START_REQUESTED,
    create_usage_session,
    mark_committed,
    mark_completed_for_machine,
    update_usage_session,
)

logger = logging.getLogger(__name__)

_scan_session_lock = threading.Lock()
_scan_sessions: dict[str, str] = {}


@dataclass
class ScanOutcome:
    success: bool
    message: str
    code_info: Optional[Any]


@dataclass
class StartOutcome:
    success: bool
    message: str
    uses_left: Optional[int]


def _provider_for_request() -> tuple[str, BaseProvider]:
    return resolve_provider()


def _lookup_mode(provider_name: str) -> str:
    return "auto" if provider_name == "reisa" else "local_code"


def _provider_reference(entitlement: Any) -> Optional[str]:
    return (
        getattr(entitlement, "external_id", None)
        or getattr(entitlement, "booking_number", None)
        or getattr(entitlement, "order_id", None)
        or getattr(entitlement, "code", None)
    )


def _resolve_or_create_session_uid(
    entitlement: Any,
    *,
    provider_name: str,
    machine_id: Optional[str],
    scan_source: Optional[str],
    identifier_type: str,
    identifier_value: Optional[str],
) -> str:
    code = getattr(entitlement, "code", None)
    if code:
        with _scan_session_lock:
            existing = _scan_sessions.pop(code, None)
        if existing:
            update_usage_session(existing, machine_id=machine_id)
            return existing

    return create_usage_session(
        provider=provider_name,
        provider_reference=_provider_reference(entitlement),
        identifier_type=identifier_type,
        identifier_value=identifier_value,
        machine_id=machine_id,
        scan_source=scan_source,
        state=STATE_SCANNED,
        requested_quantity=1,
    )


def _uses_left(entitlement: Any) -> Optional[int]:
    explicit = getattr(entitlement, "uses_left", None)
    if explicit is not None:
        try:
            return max(int(explicit), 0)
        except (TypeError, ValueError):
            return None

    usage_limit = getattr(entitlement, "usage_limit", None)
    current_usage = getattr(entitlement, "current_usage", None)
    if usage_limit is None or current_usage is None:
        return None
    try:
        return max(int(usage_limit) - int(current_usage), 0)
    except (TypeError, ValueError):
        return None


def ingest_scan(raw_code: Optional[str], source: str) -> ScanOutcome:
    """Shared scanner/API ingress orchestration."""

    provider_name, provider = _provider_for_request()
    if provider_name == "local":
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

    identifier = (raw_code or "").strip()
    ready, busy_message = require_ready_to_scan(source, identifier)
    if not ready:
        return ScanOutcome(success=False, message=busy_message or SCAN_BUSY_MESSAGE, code_info=None)
    if not identifier:
        show_error_state("Missing code")
        return ScanOutcome(success=False, message="Missing code", code_info=None)

    lookup = provider.lookup(identifier, mode=_lookup_mode(provider_name))
    if not lookup.success or not lookup.entitlement:
        message = lookup.message or "Code expired or invalid."
        show_error_state(message)
        write_scan_log(identifier, None, "invalid", source, details="provider_lookup_failed")
        return ScanOutcome(success=False, message=message, code_info=None)

    auth = provider.authorize(lookup.entitlement)
    if not auth.authorized or not auth.entitlement:
        message = auth.message or "Code expired or invalid."
        show_error_state(message)
        write_scan_log(identifier, None, "invalid", source, details="provider_unauthorized")
        return ScanOutcome(success=False, message=message, code_info=None)

    entitlement = auth.entitlement
    write_scan_log(identifier, getattr(entitlement, "order_id", None), "valid", source)
    arm_code(entitlement)
    update_ui_state(
        {
            "state": "choose_machine",
            "message": SELECT_MACHINE_MESSAGE,
            "machines": get_machine_snapshot(),
            "uses_left": _uses_left(entitlement),
            "current_machine": None,
        }
    )

    session_uid = create_usage_session(
        provider=provider_name,
        provider_reference=_provider_reference(entitlement),
        identifier_type="uuid_or_pin",
        identifier_value=identifier,
        machine_id=None,
        scan_source=source,
        state=STATE_SCANNED,
        requested_quantity=1,
    )
    code_key = getattr(entitlement, "code", identifier)
    with _scan_session_lock:
        _scan_sessions[code_key] = session_uid

    return ScanOutcome(success=True, message=SELECT_MACHINE_MESSAGE, code_info=entitlement)


def start_from_code(machine_id: Optional[str], raw_code: Optional[str]) -> StartOutcome:
    """Start flow used by API/manual paths that provide code + machine."""

    code = (raw_code or "").strip()
    if not code or not machine_id:
        return StartOutcome(success=False, message="Missing data", uses_left=None)

    provider_name, provider = _provider_for_request()
    lookup = provider.lookup(code, mode=_lookup_mode(provider_name))
    if not lookup.success:
        show_error_state(lookup.message)
        return StartOutcome(success=False, message=lookup.message, uses_left=None)

    auth = provider.authorize(lookup.entitlement, machine_id=machine_id)
    if not auth.authorized or not auth.entitlement:
        show_error_state(auth.message)
        return StartOutcome(success=False, message=auth.message, uses_left=None)

    entitlement = auth.entitlement
    session_uid = _resolve_or_create_session_uid(
        entitlement,
        provider_name=provider_name,
        machine_id=machine_id,
        scan_source="api",
        identifier_type="uuid_or_pin" if provider_name == "reisa" else "code",
        identifier_value=code,
    )
    update_usage_session(session_uid, state=STATE_AUTHORIZED, machine_id=machine_id)
    ok, message = start_machine(entitlement, machine_id, session_uid=session_uid)
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
    return StartOutcome(success=True, message=message, uses_left=_uses_left(entitlement))


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

    provider_name, provider = _provider_for_request()
    auth = provider.authorize(code_info, machine_id=machine_id)
    if not auth.authorized or not auth.entitlement:
        disarm_code()
        return StartOutcome(success=False, message=auth.message, uses_left=None)

    entitlement = auth.entitlement
    session_uid = _resolve_or_create_session_uid(
        entitlement,
        provider_name=provider_name,
        machine_id=machine_id,
        scan_source="button",
        identifier_type="uuid_or_pin" if provider_name == "reisa" else "code",
        identifier_value=getattr(entitlement, "code", None),
    )
    update_usage_session(session_uid, state=STATE_AUTHORIZED, machine_id=machine_id)
    ok, message = start_machine(entitlement, machine_id, session_uid=session_uid)
    uses_left = _uses_left(entitlement) if ok else None
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

    provider_name, provider = _provider_for_request()
    try:
        commit = provider.commit_start(pending.code, quantity=1)
        if not commit.success:
            logger.error(
                "Provider commit failed",
                extra={"machine": machine_id, "message": commit.message, "provider": provider_name},
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
            uses_left = _uses_left(pending.code)
        mark_committed(
            pending.session_uid,
            machine_id=machine_id,
            committed_quantity=1,
            remaining_after_commit=uses_left,
        )
        finalize_started_machine(machine_id, pending.code, uses_left)
    except Exception:
        logger.exception("Failed to finalize start", extra={"machine": machine_id, "provider": provider_name})
        update_usage_session(
            pending.session_uid,
            state=STATE_FAILED,
            error_code="commit_exception",
            error_detail="Exception while finalizing start commit",
        )
        show_error_state("Machine did not start. Please try again.")


def handle_run_completed(machine_id: str) -> None:
    """Persist completion lifecycle when telemetry reports run stopped."""

    updated = mark_completed_for_machine(machine_id)
    if not updated:
        logger.debug(
            "Run completion transition skipped",
            extra={"machine": machine_id},
        )


__all__ = [
    "SCAN_BUSY_MESSAGE",
    "ScanOutcome",
    "StartOutcome",
    "ValidatedCode",
    "handle_start_confirmed",
    "handle_run_completed",
    "ingest_scan",
    "start_from_button",
    "start_from_code",
]
