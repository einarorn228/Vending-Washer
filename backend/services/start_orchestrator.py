"""Start-flow orchestration entrypoints.

Phase 2 introduces provider-backed local entitlement authority while
preserving existing machine-control runtime behavior.
"""

from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)

_provider: BaseProvider = LocalProvider()


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


def ingest_scan(raw_code: Optional[str], source: str) -> ScanOutcome:
    """Shared scanner/API ingress orchestration."""

    success, message, code_info = handle_scanned_code(raw_code, source=source)
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
    ok, message = start_machine(code_info, machine_id)
    if not ok:
        show_error_state(message)
        return StartOutcome(success=False, message=message, uses_left=None)

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
    ok, message = start_machine(refreshed_code, machine_id)
    uses_left = refreshed_code.usage_limit - refreshed_code.current_usage if ok else None
    if not ok:
        show_error_state(message)
    return StartOutcome(success=ok, message=message, uses_left=uses_left)


def handle_start_confirmed(machine_id: str) -> None:
    """Continue start flow after telemetry confirms machine runstate."""

    pending = consume_pending_start(machine_id)
    if not pending:
        return
    try:
        commit = _provider.commit_start(pending.code, quantity=1)
        if not commit.success:
            logger.error(
                "Provider commit failed",
                extra={"machine": machine_id, "message": commit.message},
            )
            show_error_state("Machine did not start. Please try again.")
            return
        uses_left = commit.uses_left
        if uses_left is None:
            uses_left = max(pending.code.usage_limit - pending.code.current_usage - 1, 0)
        finalize_started_machine(machine_id, pending.code, uses_left)
    except Exception:
        logger.exception("Failed to finalize start", extra={"machine": machine_id})
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
