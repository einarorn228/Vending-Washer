"""Flask routes for touchscreen UI."""

from flask import Blueprint, jsonify, request

from backend.controllers.machine_control import (
    UI_STATE,
    arm_code,
    get_machine_snapshot,
    handle_i4_button,
    record_scan_pending,
    show_error_state,
    start_machine,
    update_ui_state,
    validate_code,
    write_scan_log,
)
from backend.models import session
from backend.models.setting_model import get_setting_value
from backend.utils.logger import get_event_logger
from backend.metrics import inc

ui_api = Blueprint("ui_api", __name__)

API_KEY_HEADER = "X-API-KEY"

events_logger = get_event_logger()


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
    if not code:
        events_logger.info(
            "SCAN received",
            extra={
                "source": "api",
                "code": code,
                "result": "invalid",
                "reason": "missing_code",
            },
        )
        inc("scan_total", outcome="rejected", reason="missing_code", source="ui")
        write_scan_log("", None, "invalid", "api", details="missing_code")
        return jsonify({"success": False, "message": "Missing code"}), 400
    code_info, msg = validate_code(code)
    if not code_info:
        reason = (msg or "invalid").rstrip(".").lower().replace(" ", "_")
        events_logger.info(
            "SCAN received",
            extra={
                "source": "api",
                "code": code,
                "result": "invalid",
                "reason": reason,
            },
        )
        update_ui_state({"state": "error", "message": msg})
        inc("scan_total", outcome="rejected", reason=reason, source="ui")
        write_scan_log(code, None, "invalid", "api", details=reason)
        return jsonify({"success": False, "message": msg})
    events_logger.info(
        "SCAN received",
        extra={"source": "api", "code": code, "result": "valid"},
    )
    inc("scan_total", outcome="accepted", source="ui")
    record_scan_pending(code)
    write_scan_log(code, code_info.order_id, "valid", "api")
    arm_code(code_info)
    machines = list_machines()
    uses_left = code_info.usage_limit - code_info.current_usage
    update_ui_state(
        {
            "state": "choose_machine",
            "message": "Please select a machine.",
            "machines": machines,
            "uses_left": uses_left,
        }
    )
    return jsonify(
        {
            "success": True,
            "uses_left": uses_left,
            "machines": machines,
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
    ok, message = handle_i4_button(index)
    status = 200 if ok else 409
    if not ok:
        show_error_state(message)
    return jsonify({"success": ok, "message": message}), status
