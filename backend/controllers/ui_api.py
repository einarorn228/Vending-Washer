"""Flask routes for touchscreen UI."""

from flask import Blueprint, request, jsonify
from models import session
from models.code_model import Code
from .machine_control import MACHINES, UI_STATE, validate_code, start_machine
from models.setting_model import get_setting_value

ui_api = Blueprint("ui_api", __name__)

API_KEY_HEADER = "X-API-KEY"


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
    if not code:
        return jsonify({"success": False, "message": "Missing code"}), 400
    obj, msg = validate_code(code)
    if not obj:
        UI_STATE.update({"state": "error", "message": msg})
        return jsonify({"success": False, "message": msg})
    UI_STATE.update(
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
    return [
        {"id": mid, "name": m["name"], "available": m["available"]}
        for mid, m in MACHINES.items()
    ]


@ui_api.route("/start_machine", methods=["POST"])
def start_machine_endpoint():
    data = request.get_json(force=True)
    code = data.get("code")
    machine_id = data.get("machine_id")
    if not code or not machine_id:
        return jsonify({"success": False, "message": "Missing data"}), 400
    obj, msg = validate_code(code)
    if not obj:
        UI_STATE.update({"state": "error", "message": msg})
        return jsonify({"success": False, "message": msg})
    ok, err = start_machine(obj, machine_id)
    if not ok:
        UI_STATE.update({"state": "error", "message": err})
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
