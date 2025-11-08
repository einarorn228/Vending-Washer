"""Machine control utilities using Shelly relays."""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional

from backend.models import session
from backend.models.code_model import Code
from backend.utils.logger import get_error_logger, get_event_logger
from backend.utils.shelly_control import send_shelly_pulse

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

    events_logger.info("UI_STATE updated: %s", summary)


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
    events_logger.info(
        "MACHINE %s start requested by code %s", machine_id, code_obj.code
    )
    machine = MACHINES.get(machine_id)
    if not machine:
        events_logger.error("MACHINE %s error: not configured", machine_id)
        return False, "Machine not available."
    if not machine.get("available", False):
        events_logger.info("MACHINE %s busy/occupied", machine_id)
        return False, "Machine not available."

    try:
        try:
            success = send_shelly_pulse(machine["ip"])
        except Exception:
            events_logger.error(
                "MACHINE %s error: relay communication failed", machine_id
            )
            error_logger.error(
                "MACHINE %s error while triggering relay", machine_id, exc_info=True
            )
            session.rollback()
            return False, "Machine start failed."

        if not success:
            events_logger.error("MACHINE %s error: Shelly command failed", machine_id)
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
        events_logger.info("MACHINE %s started", machine_id)

        if code_obj.current_usage >= code_obj.usage_limit:
            code_obj.expiration_date = datetime.utcnow() + timedelta(days=1)
        session.commit()
        threading.Timer(5, release_machine, args=[machine_id]).start()
        return True, ""
    except Exception:
        events_logger.error("MACHINE %s error: unexpected failure", machine_id)
        error_logger.error(
            "MACHINE %s unexpected error while starting", machine_id, exc_info=True
        )
        session.rollback()
        return False, "Machine start failed."


def release_machine(machine_id: str):
    with lock:
        mach = MACHINES.get(machine_id)
        if mach:
            mach["available"] = True
        else:
            events_logger.error("MACHINE %s error: unknown machine on release", machine_id)
            error_logger.error(
                "MACHINE %s encountered unknown machine on release", machine_id
            )
    update_ui_state(
        {
            "state": "waiting_for_code",
            "message": "Scan your code to start",
            "current_machine": None,
            "uses_left": None,
        }
    )
    events_logger.info("MACHINE %s finished", machine_id)
