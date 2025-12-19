"""Machine control utilities built on telemetry-backed state."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Optional, Tuple

from backend.controllers.telemetry import MachineStateStore
from backend.metrics import inc, observe_ms, set_gauge
from backend.models import Session
from backend.models.code_model import Code
from backend.models.scan_log_model import ScanLog
from backend.models.setting_model import get_setting_value, is_backend_relay_enabled
from backend.utils.logger import get_error_logger, get_event_logger
from backend.utils.shelly_control import (
    send_shelly_pulse,
    shelly_switch_off,
    shelly_switch_on,
)

logger = logging.getLogger(__name__)
events_logger = get_event_logger()
error_logger = get_error_logger()

SCAN_BUSY_MESSAGE = "System busy. Please wait."
SELECT_MACHINE_MESSAGE = "Select a machine using the physical buttons"
STARTING_INSTRUCTION_TEMPLATE = (
    "{machine} is powered on. Select a program on the machine (max 10 minutes)."
)
RUNNING_NOTICE_TEMPLATE = "{machine} started. You have {uses_left} uses left."
SELECTION_NOTICE_SECONDS = 3.0
STARTED_NOTICE_SECONDS = 3.0
SELECTION_TIMEOUT_SECONDS = 600.0
SELECTION_TIMEOUT_MESSAGE = "Selection timed out. Please scan again."


@dataclass
class ValidatedCode:
    id: Optional[int]
    code: str
    order_id: Optional[str]
    usage_limit: int
    current_usage: int


@dataclass
class PendingStart:
    code: ValidatedCode
    started_at: float
    timer: Optional[threading.Timer]


@dataclass
class ArmedCode:
    code: ValidatedCode
    expires_at: float
    timer: Optional[threading.Timer]


UI_STATE = {
    "state": "waiting_for_code",
    "message": "Scan your code to start",
    "uses_left": None,
    "current_machine": None,
    "machines": [],
}

lock = threading.Lock()
pending_lock = threading.Lock()
wait_lock = threading.Lock()
metrics_lock = threading.Lock()
armed_lock = threading.Lock()

_reset_timer: Optional[threading.Timer] = None
_pending_scans: Dict[str, float] = {}
_wait_totals = {"sum": 0.0, "count": 0}
_machine_attempts = defaultdict(int)
_machine_success = defaultdict(int)
_pending_starts: Dict[str, PendingStart] = {}
_armed_code: Optional[ArmedCode] = None

PENDING_SCAN_TTL = 600.0  # seconds

_store = MachineStateStore.instance()


def _cleanup_expired_pending_locked(now: Optional[float] = None) -> None:
    if now is None:
        now = time.perf_counter()
    cutoff = now - PENDING_SCAN_TTL
    expired = [code for code, started in _pending_scans.items() if started < cutoff]
    for code in expired:
        _pending_scans.pop(code, None)


def _cleanup_expired_pending() -> None:
    with pending_lock:
        _cleanup_expired_pending_locked()


def record_scan_pending(code: str) -> None:
    """Record when a scan was accepted to compute wait times later."""

    now = time.perf_counter()
    with pending_lock:
        _cleanup_expired_pending_locked(now)
        _pending_scans[code] = now


def _pop_wait_ms(code: str) -> Optional[int]:
    with pending_lock:
        start = _pending_scans.pop(code, None)
    if start is None:
        return None
    return int((time.perf_counter() - start) * 1000)


def _update_wait_stats(wait_ms: int) -> None:
    with wait_lock:
        _wait_totals["sum"] += wait_ms
        _wait_totals["count"] += 1
        avg = _wait_totals["sum"] / max(_wait_totals["count"], 1)
    set_gauge("avg_wait_time_ms", avg)


def _update_success_ratio(machine_id: str) -> None:
    with metrics_lock:
        attempts = _machine_attempts[machine_id]
        successes = _machine_success[machine_id]
    if attempts:
        set_gauge(
            "shelly_success_ratio",
            successes / attempts,
            machine=machine_id,
        )


def _record_failure(machine_id: str) -> None:
    inc("machine_start_failures")
    inc("machine_start_failures", machine=machine_id)
    _update_success_ratio(machine_id)


def update_ui_state(updates: Dict[str, object]) -> None:
    """Update the shared UI state and emit a concise event log entry."""

    global _reset_timer
    cancel_timer = updates.get("state") in ("waiting_for_code", "choose_machine")

    with lock:
        UI_STATE.update(updates)
        if cancel_timer and _reset_timer and _reset_timer.is_alive():
            _reset_timer.cancel()
            _reset_timer = None
        summary = {
            "state": UI_STATE.get("state"),
            "message": UI_STATE.get("message"),
            "current_machine": UI_STATE.get("current_machine"),
            "uses_left": UI_STATE.get("uses_left"),
        }

    if summary["state"] == "waiting_for_code":
        with pending_lock:
            _pending_scans.clear()
    else:
        _cleanup_expired_pending()

    events_logger.info("UI_STATE updated", extra={"ui_state": summary})


def can_accept_scan() -> bool:
    """Return True if the UI is in a state that accepts scans."""

    with lock:
        return UI_STATE.get("state") == "waiting_for_code"


def require_ready_to_scan(source: str, code: str) -> Tuple[bool, Optional[str]]:
    """Reject scans unless the UI is in the ready state."""

    if can_accept_scan():
        return True, None

    with lock:
        ui_state = UI_STATE.get("state") or "unknown"
    message = SCAN_BUSY_MESSAGE
    reason = f"busy_state_{ui_state}"
    events_logger.info(
        "SCAN received",
        extra={
            "source": source,
            "code": code,
            "result": "invalid",
            "reason": reason,
        },
    )
    inc("scan_total", outcome="rejected", reason=reason, source=source)
    write_scan_log(code, None, "invalid", source, details=reason)
    return False, message


def schedule_reset_to_ready(delay_seconds: float = 3.0) -> None:
    """Schedule a reset of the UI to the ready state after the given delay."""

    def _reset():
        update_ui_state(
            {
                "state": "waiting_for_code",
                "message": "Scan your code to start",
                "current_machine": None,
                "uses_left": None,
            }
        )

    global _reset_timer
    timer: Optional[threading.Timer] = None
    with lock:
        if _reset_timer and _reset_timer.is_alive():
            _reset_timer.cancel()
        _reset_timer = threading.Timer(delay_seconds, _reset)
        timer = _reset_timer

    if timer:
        timer.start()


def cancel_reset_timer() -> None:
    """Cancel any pending UI reset timer (primarily for tests)."""

    global _reset_timer
    with lock:
        if _reset_timer and _reset_timer.is_alive():
            _reset_timer.cancel()
        _reset_timer = None


def show_error_state(message: str, hold_seconds: int = 3) -> None:
    """Display an error message briefly before returning to the ready state."""

    update_ui_state(
        {
            "state": "error",
            "message": message,
            "current_machine": None,
            "uses_left": None,
        }
    )
    schedule_reset_to_ready(hold_seconds)


def get_machine_snapshot() -> list:
    """Return a snapshot of machine availability from the telemetry store."""

    return _store.get_snapshot()


def _get_session():
    return Session()


def validate_code(code: str) -> Tuple[Optional[ValidatedCode], str]:
    """Return ValidatedCode if valid and not expired/overused."""

    db = _get_session()
    try:
        obj = db.query(Code).filter_by(code=code).first()
        if not obj:
            return None, "Code expired or invalid."
        if obj.expiration_date and obj.expiration_date <= datetime.utcnow():
            return None, "Code expired or invalid."
        if obj.current_usage >= obj.usage_limit:
            return None, "Code expired or invalid."
        return (
            ValidatedCode(
                id=getattr(obj, "id", None),
                code=obj.code,
                order_id=obj.order_id,
                usage_limit=obj.usage_limit,
                current_usage=obj.current_usage,
            ),
            "",
        )
    finally:
        db.close()


def _reason_from_message(message: str) -> str:
    return (message or "invalid").rstrip(".").lower().replace(" ", "_")


def _machine_display_name(machine_id: str) -> str:
    runtime = _store.get_machine(machine_id)
    return runtime.ui_name if runtime else machine_id


def handle_scanned_code(
    raw_code: Optional[str], source: str
) -> Tuple[bool, str, Optional[ValidatedCode]]:
    """Shared handler for scans from HTTP or physical scanner."""

    code = (raw_code or "").strip()
    ready, message = require_ready_to_scan(source, code)
    if not ready:
        return False, message or "System busy. Please wait.", None

    if not code:
        events_logger.info(
            "SCAN received",
            extra={
                "source": source,
                "code": code,
                "result": "invalid",
                "reason": "missing_code",
            },
        )
        inc("scan_total", outcome="rejected", reason="missing_code", source=source)
        write_scan_log("", None, "invalid", source, details="missing_code")
        update_ui_state({"state": "error", "message": "Missing code"})
        return False, "Missing code", None

    code_info, msg = validate_code(code)
    if not code_info:
        reason = _reason_from_message(msg)
        events_logger.info(
            "SCAN received",
            extra={
                "source": source,
                "code": code,
                "result": "invalid",
                "reason": reason,
            },
        )
        update_ui_state({"state": "error", "message": msg})
        inc("scan_total", outcome="rejected", reason=reason, source=source)
        write_scan_log(code, None, "invalid", source, details=reason)
        return False, msg, None

    events_logger.info(
        "SCAN received",
        extra={"source": source, "code": code, "result": "valid"},
    )
    inc("scan_total", outcome="accepted", source=source)
    record_scan_pending(code)
    write_scan_log(code, code_info.order_id, "valid", source)
    arm_code(code_info)
    machines = get_machine_snapshot()
    uses_left = code_info.usage_limit - code_info.current_usage
    update_ui_state(
        {
            "state": "choose_machine",
            "message": SELECT_MACHINE_MESSAGE,
            "machines": machines,
            "uses_left": uses_left,
            "current_machine": None,
        }
    )
    return True, SELECT_MACHINE_MESSAGE, code_info


def write_scan_log(
    code_value: str,
    order_id: Optional[str],
    result: str,
    source: str,
    details: Optional[str] = None,
) -> None:
    """Persist scan attempts to the scan_logs table."""

    db = _get_session()
    try:
        entry = ScanLog(
            code=code_value,
            order_id=order_id,
            result=result,
            details=details or source,
        )
        db.add(entry)
        db.commit()
    except Exception:  # pragma: no cover - defensive logging
        db.rollback()
        error_logger.exception(
            "Failed to record scan log",
            extra={"code": code_value, "source": source, "result": result},
        )
    finally:
        db.close()


def _apply_usage_delta(code_info: ValidatedCode) -> int:
    db = _get_session()
    try:
        obj = db.query(Code).filter_by(code=code_info.code).first()
        if not obj:
            error_logger.error(
                "Code not found when applying usage delta", extra={"code": code_info.code}
            )
            return code_info.usage_limit - code_info.current_usage
        obj.current_usage += 1
        uses_left = max(obj.usage_limit - obj.current_usage, 0)
        if obj.current_usage >= obj.usage_limit:
            obj.expiration_date = datetime.utcnow() + timedelta(days=1)
        db.commit()
        return uses_left
    except Exception:
        db.rollback()
        error_logger.exception("Failed to debit code", extra={"code": code_info.code})
        raise
    finally:
        db.close()


def _show_program_started(machine_id: str, uses_left: int) -> str:
    machine_name = _machine_display_name(machine_id)
    message = RUNNING_NOTICE_TEMPLATE.format(machine=machine_name, uses_left=uses_left)
    update_ui_state(
        {
            "state": "machine_in_use",
            "message": message,
            "current_machine": machine_id,
            "uses_left": uses_left,
            "machines": get_machine_snapshot(),
        }
    )
    cancel_reset_timer()
    schedule_reset_to_ready(STARTED_NOTICE_SECONDS)
    return message


def _handle_successful_start(machine_id: str, code_info: ValidatedCode) -> None:
    uses_left = _apply_usage_delta(code_info)
    with metrics_lock:
        _machine_success[machine_id] += 1
    _update_success_ratio(machine_id)
    inc("machines_started_total")
    inc("machines_started_total", machine=machine_id)
    inc("scan_total", outcome="success", source="ui")
    wait_ms = _pop_wait_ms(code_info.code)
    if wait_ms is not None:
        observe_ms("scan_to_start_ms", wait_ms)
        _update_wait_stats(wait_ms)
    message = _show_program_started(machine_id, uses_left)
    events_logger.info(
        "START_CONFIRMED",
        extra={
            "machine": machine_id,
            "code": code_info.code,
            "uses_left": uses_left,
            "message": message,
        },
    )


def _selection_timeout(machine_id: str) -> None:
    pending = _pending_starts.pop(machine_id, None)
    _store.clear_pending_start(machine_id)
    if pending and pending.timer:
        pending.timer.cancel()
    events_logger.info(
        "SELECTION_TIMEOUT",
        extra={"machine": machine_id, "notice": SELECTION_TIMEOUT_MESSAGE},
    )
    with lock:
        ui_state = UI_STATE.get("state")
        current_machine = UI_STATE.get("current_machine")
    if ui_state == "machine_starting" and current_machine == machine_id:
        update_ui_state(
            {
                "state": "waiting_for_code",
                "message": "Scan your code to start",
                "current_machine": None,
                "uses_left": None,
                "machines": get_machine_snapshot(),
            }
        )


def _on_runstate_started(machine_id: str) -> None:
    pending = _pending_starts.pop(machine_id, None)
    _store.clear_pending_start(machine_id)
    if not pending:
        return
    if pending.timer:
        pending.timer.cancel()
    try:
        _handle_successful_start(machine_id, pending.code)
    except Exception:
        error_logger.exception(
            "Failed to finalize start", extra={"machine": machine_id}
        )
        show_error_state("Machine did not start. Please try again.")


def _on_device_offline(machine_id: str) -> None:
    if machine_id in _pending_starts:
        events_logger.warning("START_FAILED_OFFLINE", extra={"machine": machine_id})
        with lock:
            ui_state = UI_STATE.get("state")
        if ui_state in {"machine_starting", "choose_machine"}:
            update_ui_state({"machines": get_machine_snapshot()})


_store.add_listener("runstate_started", _on_runstate_started)
_store.add_listener("device_offline", _on_device_offline)


def _selection_timeout_seconds() -> float:
    db = _get_session()
    try:
        raw = get_setting_value(db, "selection_timeout_sec")
    finally:
        db.close()
    try:
        value = float(raw)
        if value > 0:
            return value
    except (TypeError, ValueError):
        pass
    return SELECTION_TIMEOUT_SECONDS


def _button_timeout_seconds() -> int:
    db = _get_session()
    try:
        raw = get_setting_value(db, "button_select_timeout_sec")
    finally:
        db.close()
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 45


def _deactivate_button_box() -> None:
    device = _store.get_device_by_role("button_box")
    if not device:
        return
    if device.metric_source == "pulse":
        ok = send_shelly_pulse(device.ip, relay=device.relay_channel or 0, duration=1)
    else:
        ok = shelly_switch_off(device)
    if ok:
        events_logger.info("BUTTON_BOX_OFF")
    else:
        events_logger.warning("BUTTON_BOX_OFF_FAILED")


def _activate_button_box() -> None:
    device = _store.get_device_by_role("button_box")
    if not device:
        return
    if shelly_switch_on(device):
        events_logger.info("BUTTON_BOX_ON")
    else:
        events_logger.warning("BUTTON_BOX_ON_FAILED")


def _clear_armed_code_locked() -> None:
    global _armed_code
    if _armed_code and _armed_code.timer:
        _armed_code.timer.cancel()
    _armed_code = None


def arm_code(code_info: ValidatedCode) -> None:
    """Keep the validated code available for i4 button presses."""

    timeout = max(_button_timeout_seconds(), 1)
    expires_at = time.monotonic() + timeout

    def _timeout():
        with armed_lock:
            if not _armed_code or _armed_code.code.code != code_info.code:
                return
            events_logger.info("BUTTON_SELECT_TIMEOUT", extra={"code": code_info.code})
            _deactivate_button_box()
            _clear_armed_code_locked()
        show_error_state("No selection detected. Please scan again.")

    with armed_lock:
        global _armed_code
        _clear_armed_code_locked()
        timer = threading.Timer(timeout, _timeout)
        _armed_code = ArmedCode(code=code_info, expires_at=expires_at, timer=timer)
        timer.start()
    _activate_button_box()


def disarm_code() -> None:
    with armed_lock:
        if not _armed_code:
            return
        _deactivate_button_box()
        _clear_armed_code_locked()


def _get_active_code_info() -> Optional[ValidatedCode]:
    """Return the currently armed code if still valid and not expired."""

    now = time.monotonic()
    with armed_lock:
        armed = _armed_code
        if not armed:
            return None
        if armed.expires_at < now:
            _deactivate_button_box()
            _clear_armed_code_locked()
            return None
        return armed.code


def _resolve_machine(machine_id: str):
    runtime = _store.get_machine(machine_id)
    if not runtime or not runtime.is_enabled:
        return None
    return runtime


def _enter_machine_starting_state(machine_id: str, code_info: ValidatedCode) -> str:
    machine_name = _machine_display_name(machine_id)
    message = STARTING_INSTRUCTION_TEMPLATE.format(machine=machine_name)
    update_ui_state(
        {
            "state": "machine_starting",
            "message": message,
            "current_machine": machine_id,
            "uses_left": code_info.usage_limit - code_info.current_usage,
            "machines": get_machine_snapshot(),
        }
    )
    cancel_reset_timer()
    schedule_reset_to_ready(SELECTION_NOTICE_SECONDS)
    events_logger.info(
        "MACHINE_STARTING_UI",
        extra={"machine": machine_id, "code": code_info.code},
    )
    return message


def start_machine(code_info: ValidatedCode, machine_id: str):
    """Trigger machine relay and wait for telemetry confirmation."""

    runtime = _resolve_machine(machine_id)
    if not runtime:
        events_logger.error("MACHINE error: not configured", extra={"machine": machine_id})
        _record_failure(machine_id)
        return False, "Machine not available."

    if not runtime.available:
        events_logger.info("MACHINE busy", extra={"machine": machine_id})
        _record_failure(machine_id)
        return False, "Machine not available."

    disarm_code()

    inc("machine_start_attempts")
    inc("machine_start_attempts", machine=machine_id)
    with metrics_lock:
        _machine_attempts[machine_id] += 1

    db = _get_session()
    try:
        backend_control_enabled = is_backend_relay_enabled(db)
    finally:
        db.close()
    events_logger.info(
        "START_REQUESTED",
        extra={
            "machine": machine_id,
            "code": code_info.code,
            "backend_relay": backend_control_enabled,
        },
    )

    existing_pending = _pending_starts.pop(machine_id, None)
    if existing_pending and existing_pending.timer:
        existing_pending.timer.cancel()

    _store.mark_pending_start(machine_id)
    start_message = _enter_machine_starting_state(machine_id, code_info)

    success = True
    if backend_control_enabled:
        try:
            success = shelly_switch_on(runtime.uni_device)
        except Exception:
            success = False
            error_logger.exception(
                "Relay communication failed", extra={"machine": machine_id}
            )

        if not success:
            _store.clear_pending_start(machine_id)
            events_logger.error(
                "MACHINE error: Shelly command failed", extra={"machine": machine_id}
            )
            _record_failure(machine_id)
            return False, "Machine start failed."

        events_logger.info(
            "MACHINE relay start sent", extra={"machine": machine_id, "backend_relay": True}
        )
    else:
        events_logger.info(
            "MACHINE backend relay disabled; skipping Shelly command",
            extra={"machine": machine_id, "backend_relay": False},
        )

    timer = threading.Timer(_selection_timeout_seconds(), _selection_timeout, args=[machine_id])
    timer.start()
    _pending_starts[machine_id] = PendingStart(
        code=code_info,
        started_at=time.monotonic(),
        timer=timer,
    )
    return True, start_message


def start_machine_from_button(machine_id: str) -> Tuple[bool, str, Optional[int]]:
    code_info = _get_active_code_info()
    if not code_info:
        events_logger.info(
            "MACHINE start rejected", extra={"machine": machine_id, "reason": "no_code"}
        )
        return False, "No valid scan in progress.", None

    fresh_code_info, msg = validate_code(code_info.code)
    if not fresh_code_info:
        events_logger.info(
            "MACHINE start rejected",
            extra={"machine": machine_id, "reason": msg or "invalid_code"},
        )
        disarm_code()
        return False, msg, None

    uses_left = fresh_code_info.usage_limit - fresh_code_info.current_usage
    ok, message = start_machine(fresh_code_info, machine_id)
    return ok, message, uses_left if ok else None


def handle_i4_button(button_index: int) -> Tuple[bool, str, Optional[int]]:
    machine_id = _store.resolve_button(button_index)
    if not machine_id:
        events_logger.warning("I4_BUTTON_UNKNOWN", extra={"button": button_index})
        return False, "Unknown button.", None
    events_logger.info("I4_BUTTON_PRESS", extra={"button": button_index, "machine": machine_id})
    return start_machine_from_button(machine_id)
