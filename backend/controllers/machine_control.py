"""Machine control utilities using Shelly relays."""

import logging
import threading
from typing import Dict

from backend.models import session
from backend.models.code_model import Code
from backend.utils.shelly_control import send_shelly_pulse

logger = logging.getLogger(__name__)

MACHINES: Dict[str, dict] = {
    "washer1": {"name": "Washer 1", "available": True, "ip": "192.168.107.11"},
    "washer2": {"name": "Dryer 1", "available": True, "ip": "192.168.107.12"},
    "washer1": {"name": "Washer 2", "available": True, "ip": "192.168.107.13"},
    "washer2": {"name": "Dryer 2", "available": True, "ip": "192.168.107.14"},
}

UI_STATE = {
    "state": "waiting_for_code",
    "message": "Scan your code to start",
    "uses_left": None,
    "current_machine": None,
    "machines": [],
}

lock = threading.Lock()


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


from datetime import datetime, timedelta


def start_machine(code_obj: Code, machine_id: str):
    """Trigger machine relay and update usage."""
    machine = MACHINES.get(machine_id)
    if not machine or not machine["available"]:
        return False, "Machine not available."
    success = send_shelly_pulse(machine["ip"])
    if not success:
        return False, "Machine start failed."
    with lock:
        machine["available"] = False
        UI_STATE.update(
            {
                "state": "machine_in_use",
                "message": "Machine started!",
                "current_machine": machine_id,
                "uses_left": code_obj.usage_limit - code_obj.current_usage - 1,
            }
        )
    code_obj.current_usage += 1
    if code_obj.current_usage >= code_obj.usage_limit:
        code_obj.expiration_date = datetime.utcnow() + timedelta(days=1)
    session.commit()
    threading.Timer(5, release_machine, args=[machine_id]).start()
    return True, ""


def release_machine(machine_id: str):
    with lock:
        mach = MACHINES.get(machine_id)
        if mach:
            mach["available"] = True
        UI_STATE.update(
            {
                "state": "waiting_for_code",
                "message": "Ready",
                "current_machine": None,
                "uses_left": None,
            }
        )
