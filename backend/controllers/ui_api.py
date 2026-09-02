"""Flask routes for touchscreen UI."""
import logging
from flask import Blueprint, jsonify, request

from backend.controllers.machine_control import (
    UI_STATE,
    get_machine_snapshot,
    reservation_minutes,
    SELECT_MACHINE_MESSAGE,
)
from backend.models import session
from backend.models.setting_model import get_setting_value, is_button_box_enabled
from backend.metrics import inc
from backend.services.start_orchestrator import (
    SCAN_BUSY_MESSAGE,
    ingest_scan,
    start_from_button,
    start_from_code,
    start_from_touch,
)

ui_api = Blueprint("ui_api", __name__)

API_KEY_HEADER = "X-API-KEY"


INPUT_MODE_TOUCH = "touch"
INPUT_MODE_HARDWARE_BUTTONS = "hardware_buttons"

_log = logging.getLogger(__name__)


DEFAULT_POLL_INTERVAL_MS = 1000


def _resolve_poll_interval_ms() -> int:
    raw = get_setting_value(session, "kiosk_poll_interval_ms", default=DEFAULT_POLL_INTERVAL_MS)
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        return DEFAULT_POLL_INTERVAL_MS
    if not 250 <= value <= 10000:
        return DEFAULT_POLL_INTERVAL_MS
    return value


def _resolve_input_mode() -> str:
    raw_mode = get_setting_value(session, "kiosk_input_mode", default=INPUT_MODE_HARDWARE_BUTTONS)
    mode = str(raw_mode or "").strip().lower()
    if mode == INPUT_MODE_TOUCH:
        return INPUT_MODE_TOUCH
    return INPUT_MODE_HARDWARE_BUTTONS



@ui_api.before_request
def check_api_key():
    key = request.headers.get(API_KEY_HEADER) or request.args.get("api_key")
    db_key = get_setting_value(session, "api_key")
    if not key or key != db_key:
        inc("http_auth_failures", endpoint=request.path or "ui_api")
        return jsonify({"success": False, "message": "Invalid API key"}), 401


@ui_api.route("/scan_code", methods=["POST"])
def scan_code():
    data = request.get_json(force=True)
    code = data.get("code")
    outcome = ingest_scan(code, source="api")
    if not outcome.success:
        message = outcome.message
        status = 409 if message == SCAN_BUSY_MESSAGE else 400
        return jsonify({"success": False, "message": message}), status
    machines = list_machines()
    code_info = outcome.code_info
    uses_left = code_info.usage_limit - code_info.current_usage if code_info else None
    return jsonify(
        {
            "success": True,
            "uses_left": uses_left,
            "machines": machines,
            "message": SELECT_MACHINE_MESSAGE,
        }
    )


def list_machines():
    return get_machine_snapshot()


def _machine_exists(machine_id: str) -> bool:
    return any(machine.get("id") == machine_id for machine in list_machines())


@ui_api.route("/start_machine", methods=["POST"])
def start_machine_endpoint():
    data = request.get_json(force=True)
    code = data.get("code")
    machine_id = data.get("machine_id")
    outcome = start_from_code(machine_id=machine_id, raw_code=code)
    if not outcome.success:
        status = 400 if outcome.message == "Missing data" else 409
        return jsonify({"success": False, "message": outcome.message}), status
    return jsonify(
        {
            "success": True,
            "uses_left": outcome.uses_left,
            "message": outcome.message,
        }
    )


@ui_api.route("/touch_select_machine", methods=["POST"])
def touch_select_machine_endpoint():
    data = request.get_json(force=True, silent=True) or {}
    machine_id = (data.get("machine_id") or "").strip()
    if not machine_id:
        return jsonify({"success": False, "message": "Missing machine_id"}), 400
    if not _machine_exists(machine_id):
        return jsonify({"success": False, "message": "Invalid machine_id"}), 400
    if UI_STATE.get("state") != "choose_machine":
        return (
            jsonify({"success": False, "message": "Machine selection is not active.", "state": UI_STATE.get("state")}),
            409,
        )

    outcome = start_from_touch(machine_id=machine_id)
    status = 200 if outcome.success else 409
    return (
        jsonify(
            {
                "success": outcome.success,
                "message": outcome.message,
                "uses_left": outcome.uses_left,
                "state": UI_STATE.get("state"),
            }
        ),
        status,
    )


@ui_api.route("/ui_state", methods=["GET"])
def ui_state():
    state = UI_STATE.copy()
    state["machines"] = list_machines()
    state["input_mode"] = _resolve_input_mode()
    state["button_box_enabled"] = is_button_box_enabled(session)
    state["reservation_minutes"] = reservation_minutes()
    state["poll_interval_ms"] = _resolve_poll_interval_ms()
    response = jsonify(state)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@ui_api.route("/i4_event", methods=["POST", "GET"])
def i4_event():
    if request.method == "GET":
        button = request.args.get("button")
    else:
        data = request.get_json(force=True, silent=True) or {}
        button = data.get("button")
    if button is None:
        return jsonify({"success": False, "message": "Missing button index"}), 400
    try:
        index = int(button)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid button index"}), 400
    if not is_button_box_enabled(session):
        _log.info("I4_BUTTON_IGNORED", extra={"reason": "button_box_disabled", "button": index})
        return jsonify({"success": False, "message": "Button box input is disabled."}), 409
    outcome = start_from_button(index)
    status = 200 if outcome.success else 409
    return jsonify(
        {
            "success": outcome.success,
            "message": outcome.message,
            "uses_left": outcome.uses_left,
        }
    ), status
