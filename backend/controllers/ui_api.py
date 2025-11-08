"""Flask routes for touchscreen UI."""

from flask import Blueprint, jsonify, request

from backend.controllers.machine_control import (
    UI_STATE,
    get_machine_snapshot,
    show_error_state,
    start_machine,
    update_ui_state,
    validate_code,
)
from backend.models import session
from backend.models.setting_model import get_setting_value
from backend.utils.logger import get_event_logger

ui_api = Blueprint("ui_api", __name__)

API_KEY_HEADER = "X-API-KEY"

events_logger = get_event_logger()


@ui_api.before_request
def check_api_key():
    key = request.headers.get(API_KEY_HEADER)
    db_key = get_setting_value(session, "api_key")
    if not key or key != db_key:
        return jsonify({"success": False, "message": "Invalid API key"}), 401


@ui_api.route("/scan_code", methods=["POST"])
def scan_code():
    data = request.get_json(force=True)
    code = data.get("code")
    events_logger.info("SCAN started (api)")
    if not code:
        events_logger.info("SCAN rejected: <missing> (invalid)")
        return jsonify({"success": False, "message": "Missing code"}), 400
    obj, msg = validate_code(code)
    if not obj:
        events_logger.info("SCAN rejected: %s (invalid)", code)
        show_error_state(msg)
        return jsonify({"success": False, "message": msg})
    events_logger.info("SCAN accepted: %s", code)
    update_ui_state(
        {
            "state": "choose_machine",
            "message": "Please select a machine.",
            "machines": list_machines(),
            "uses_left": obj.usage_limit - obj.current_usage,
        }
    )
    return jsonify(
        {
            "success": True,
            "uses_left": obj.usage_limit - obj.current_usage,
            "machines": list_machines(),
            "message": "Please select a machine.",
        }
    )


def list_machines():
    return get_machine_snapshot()


@ui_api.route("/start_machine", methods=["POST"])
def start_machine_endpoint():
    data = request.get_json(force=True)
    code = data.get("code")
    machine_id = data.get("machine_id")
    if not code or not machine_id:
        return jsonify({"success": False, "message": "Missing data"}), 400
    obj, msg = validate_code(code)
    if not obj:
        show_error_state(msg)
        return jsonify({"success": False, "message": msg})
    ok, err = start_machine(obj, machine_id)
    if not ok:
        show_error_state(err)
        return jsonify({"success": False, "message": err})
    return jsonify(
        {
            "success": True,
            "uses_left": obj.usage_limit - obj.current_usage,
            "message": "Machine started! You have %d uses left."
            % (obj.usage_limit - obj.current_usage),
        }
    )


@ui_api.route("/ui_state", methods=["GET"])
def ui_state():
    state = UI_STATE.copy()
    state["machines"] = list_machines()
    return jsonify(state)
