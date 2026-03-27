"""Start-flow orchestration entrypoints.

Phase 1 extracts orchestration call-shape from controllers while preserving
current local machine-control behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from backend.controllers.machine_control import (
    SCAN_BUSY_MESSAGE,
    ValidatedCode,
    consume_pending_start,
    finalize_successful_start,
    handle_i4_button,
    handle_scanned_code,
    show_error_state,
    start_machine,
    validate_code,
)

logger = logging.getLogger(__name__)


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

    code_info, msg = validate_code(code)
    if not code_info:
        show_error_state(msg)
        return StartOutcome(success=False, message=msg, uses_left=None)

    ok, message = start_machine(code_info, machine_id)
    if not ok:
        show_error_state(message)
        return StartOutcome(success=False, message=message, uses_left=None)

    uses_left = code_info.usage_limit - code_info.current_usage
    return StartOutcome(success=True, message=message, uses_left=uses_left)


def start_from_button(button_index: int) -> StartOutcome:
    """Start flow for i4 button callbacks."""

    ok, message, uses_left = handle_i4_button(button_index)
    if not ok:
        show_error_state(message)
    return StartOutcome(success=ok, message=message, uses_left=uses_left)


def handle_start_confirmed(machine_id: str) -> None:
    """Continue start flow after telemetry confirms machine runstate."""

    pending = consume_pending_start(machine_id)
    if not pending:
        return
    try:
        finalize_successful_start(machine_id, pending.code)
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
