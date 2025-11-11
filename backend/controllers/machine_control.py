"""Machine control utilities using Shelly relays."""

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional

from backend.models import session
from backend.models.code_model import Code
from backend.utils.logger import get_error_logger, get_event_logger
from backend.utils.shelly_control import send_shelly_pulse
from backend.metrics import inc, observe_ms, set_gauge

logger = logging.getLogger(__name__)
events_logger = get_event_logger()
error_logger = get_error_logger()

MACHINES: Dict[str, dict] = {
    "washer1": {"name": "Washer 1", "available": True, "ip": "192.168.107.11"},
    "dryer1": {"name": "Dryer 1", "available": True, "ip": "192.168.107.12"},
    "washer2": {"name": "Washer 2", "available": True, "ip": "192.168.107.13"},
    "dryer2": {"name": "Dryer 2", "available": True, "ip": "192.168.107.14"},
}

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

_pending_scans: Dict[str, float] = {}
_wait_totals = {"sum": 0.0, "count": 0}
_machine_attempts = defaultdict(int)
_machine_success = defaultdict(int)

PENDING_SCAN_TTL = 600.0  # seconds


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

_reset_timer: Optional[threading.Timer] = None


def update_ui_state(updates: Dict[str, object]) -> None:
    """Update the shared UI state and emit a concise event log entry."""

    global _reset_timer
    cancel_timer = updates.get("state") not in (None, "error")

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


def schedule_reset_to_ready(delay_seconds: int = 3) -> None:
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


def get_machine_snapshot():
    """Return a thread-safe snapshot of machine availability."""

    with lock:
        return [
            {
                "id": machine_id,
                "name": machine["name"],
                "available": machine["available"],
            }
            for machine_id, machine in MACHINES.items()
        ]


def validate_code(code: str):
    """Return Code object if valid and not expired/overused."""
    obj = session.query(Code).filter_by(code=code).first()
    if not obj:
        return None, "Code expired or invalid."
    if obj.expiration_date and obj.expiration_date <= datetime.utcnow():
        return None, "Code expired or invalid."
    if obj.current_usage >= obj.usage_limit:
        return None, "Code expired or invalid."
    return obj, ""


def start_machine(code_obj: Code, machine_id: str):
    """Trigger machine relay and update usage."""

    inc("machine_start_attempts")
    inc("machine_start_attempts", machine=machine_id)
    with metrics_lock:
        _machine_attempts[machine_id] += 1
    events_logger.info(
        "MACHINE start requested",
        extra={"machine_id": machine_id, "code": code_obj.code},
    )
    machine = MACHINES.get(machine_id)
    if not machine:
        events_logger.error(
            "MACHINE error: not configured", extra={"machine_id": machine_id}
        )
        _record_failure(machine_id)
        return False, "Machine not available."
    if not machine.get("available", False):
        events_logger.info(
            "MACHINE busy", extra={"machine_id": machine_id}
        )
        _record_failure(machine_id)
        return False, "Machine not available."

    try:
        try:
            success = send_shelly_pulse(machine["ip"])
        except Exception:
            events_logger.error(
                "MACHINE error: relay communication failed",
                extra={"machine_id": machine_id},
            )
            error_logger.error(
                "MACHINE error while triggering relay",
                extra={"machine_id": machine_id},
                exc_info=True,
            )
            session.rollback()
            _record_failure(machine_id)
            return False, "Machine start failed."

        if not success:
            events_logger.error(
                "MACHINE error: Shelly command failed",
                extra={"machine_id": machine_id},
            )
            _record_failure(machine_id)
            return False, "Machine start failed."

        with lock:
            machine["available"] = False

        code_obj.current_usage += 1
        uses_left = max(code_obj.usage_limit - code_obj.current_usage, 0)
        update_ui_state(
            {
                "state": "machine_in_use",
                "message": "Machine started!",
                "current_machine": machine_id,
                "uses_left": uses_left,
            }
        )
        events_logger.info("MACHINE started", extra={"machine_id": machine_id})
        inc("machines_started_total")
        inc("machines_started_total", machine=machine_id)
        with metrics_lock:
            _machine_success[machine_id] += 1
        _update_success_ratio(machine_id)
        inc("scan_total", outcome="success", source="ui")

        wait_ms = _pop_wait_ms(code_obj.code)
        if wait_ms is not None:
            observe_ms("scan_to_start_ms", wait_ms)
            _update_wait_stats(wait_ms)

        if code_obj.current_usage >= code_obj.usage_limit:
            code_obj.expiration_date = datetime.utcnow() + timedelta(days=1)
        session.commit()
        threading.Timer(5, release_machine, args=[machine_id]).start()
        return True, ""
    except Exception:
        events_logger.error(
            "MACHINE error: unexpected failure", extra={"machine_id": machine_id}
        )
        error_logger.error(
            "MACHINE unexpected error while starting",
            extra={"machine_id": machine_id},
            exc_info=True,
        )
        session.rollback()
        _record_failure(machine_id)
        return False, "Machine start failed."


def release_machine(machine_id: str):
    with lock:
        mach = MACHINES.get(machine_id)
        if mach:
            mach["available"] = True
        else:
            events_logger.error(
                "MACHINE error: unknown machine on release",
                extra={"machine_id": machine_id},
            )
            error_logger.error(
                "MACHINE encountered unknown machine on release",
                extra={"machine_id": machine_id},
            )
    update_ui_state(
        {
            "state": "waiting_for_code",
            "message": "Scan your code to start",
            "current_machine": None,
            "uses_left": None,
        }
    )
    events_logger.info("MACHINE finished", extra={"machine_id": machine_id})
    inc("sessions_completed_total")
    inc("sessions_completed_total", machine=machine_id)
