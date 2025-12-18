"""Flask routes for touchscreen UI."""
from flask import Blueprint, jsonify, request

from backend.controllers.machine_control import (
    SCAN_BUSY_MESSAGE,
    SELECT_MACHINE_MESSAGE,
    UI_STATE,
    get_machine_snapshot,
    handle_i4_button,
    handle_scanned_code,
    show_error_state,
    start_machine,
    validate_code,
)
from backend.models import session
from backend.models.setting_model import get_setting_value
from backend.metrics import inc

ui_api = Blueprint("ui_api", __name__)

API_KEY_HEADER = "X-API-KEY"


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
    success, message, code_info = handle_scanned_code(code, source="api")
    if not success:
        status = 409 if message == SCAN_BUSY_MESSAGE else 400
        return jsonify({"success": False, "message": message}), status
    machines = list_machines()
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


@ui_api.route("/start_machine", methods=["POST"])
def start_machine_endpoint():
    data = request.get_json(force=True)
    code = data.get("code")
    machine_id = data.get("machine_id")
    if not code or not machine_id:
        return jsonify({"success": False, "message": "Missing data"}), 400
    code_info, msg = validate_code(code)
    if not code_info:
        show_error_state(msg)
        return jsonify({"success": False, "message": msg})
    ok, message = start_machine(code_info, machine_id)
    if not ok:
        show_error_state(message)
        return jsonify({"success": False, "message": message})
    return jsonify(
        {
            "success": True,
            "uses_left": code_info.usage_limit - code_info.current_usage,
            "message": message,
        }
    )


@ui_api.route("/ui_state", methods=["GET"])
def ui_state():
    state = UI_STATE.copy()
    state["machines"] = list_machines()
    return jsonify(state)


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
    ok, message, uses_left = handle_i4_button(index)
    status = 200 if ok else 409
    if not ok:
        show_error_state(message)
    return jsonify({"success": ok, "message": message, "uses_left": uses_left}), status
