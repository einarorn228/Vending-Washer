"""Temporary beta/dev admin API.

This blueprint is intentionally protected by a backend kill switch and API-key
check, then narrowed further by service-layer whitelists. It is not a production
admin system.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from functools import wraps

from flask import Blueprint, jsonify, request


from backend.metrics import inc
from backend.models import Session
from backend.models.setting_model import get_setting_value, parse_setting_bool
from backend.services.dev_admin_service import (
    apply_machine_order,
    apply_machine_update,
    apply_settings_changes,
    build_export_config,
    build_grouped_settings,
    build_machines_payload,
    build_status,
    validate_machine_order,
    validate_machine_update,
    validate_settings_changes,
)

DEV_ADMIN_DISABLED_MESSAGE = "Beta dev/admin panel is disabled."
API_KEY_HEADER = "X-API-KEY"

dev_admin_api = Blueprint("dev_admin_api", __name__)


def _json_error(message: str, status: int, **extra):
    payload = {"success": False, "message": message}
    payload.update(extra)
    return jsonify(payload), status


def _is_enabled(db) -> bool:
    raw = get_setting_value(db, "dev_admin_enabled", default="false")
    return parse_setting_bool(raw, default=False)


def _valid_admin_auth(db) -> bool:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        b64 = auth_header.split(" ", 1)[1]
        userpass = base64.b64decode(b64).decode("utf-8")
        username, password = userpass.split(":", 1)
    except Exception:
        return False
    db_user = get_setting_value(db, "admin_username")
    db_pass_hash = get_setting_value(db, "admin_password_hash")
    if db_user is None or db_pass_hash is None:
        return False
    pass_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return username == db_user and pass_hash == db_pass_hash


def require_dev_admin(view_function):
    @wraps(view_function)
    def decorated(*args, **kwargs):
        db = Session()
        try:
            if not _is_enabled(db):
                return _json_error(DEV_ADMIN_DISABLED_MESSAGE, 403, disabled=True)
            if not _valid_admin_auth(db):
                inc("http_auth_failures", endpoint=request.path or "dev_admin")
                return _json_error("Invalid credentials", 401)
            return view_function(db, *args, **kwargs)
        finally:
            db.close()

    return decorated


@dev_admin_api.route("/unlock", methods=["POST"])
@require_dev_admin
def unlock(db):
    return jsonify({"success": True, "message": "Unlocked", "temporary": True})


@dev_admin_api.route("/status", methods=["GET"])
@require_dev_admin
def status(db):
    return jsonify({"success": True, "status": build_status(db)})


@dev_admin_api.route("/settings", methods=["GET"])
@require_dev_admin
def settings(db):
    payload = build_grouped_settings(db)
    return jsonify({"success": True, **payload})


@dev_admin_api.route("/settings", methods=["PATCH"])
@require_dev_admin
def update_settings(db):
    data = request.get_json(silent=True) or {}
    changes = dict(data.get("changes") or {})
    
    sensitive_updates = {}
    
    # Require current API key if updating sensitive tokens
    if "reisa_bearer_token" in changes or "api_key" in changes:
        current_key = data.get("current_api_key")
        db_key = get_setting_value(db, "api_key")
        if not current_key or current_key != db_key:
            return jsonify({"success": False, "message": "Current API Key is incorrect or missing.", "errors": {}}), 403
            
        if "reisa_bearer_token" in changes:
            sensitive_updates["reisa_bearer_token"] = changes.pop("reisa_bearer_token")
        if "api_key" in changes:
            sensitive_updates["api_key"] = changes.pop("api_key")

    validated, errors = validate_settings_changes(db, changes)
    if errors:
        return jsonify({"success": False, "message": "Invalid settings update.", "errors": errors}), 400
    try:
        updated = apply_settings_changes(db, validated or {})
        
        if sensitive_updates:
            from backend.models.setting_model import update_setting_value
            for skey, sval in sensitive_updates.items():
                update_setting_value(db, skey, str(sval))
                updated.append({"key": skey, "value": "***", "restart_required": False})
            
    except Exception:
        db.rollback()
        raise
    return jsonify({"success": True, "updated": updated, "errors": {}})

@dev_admin_api.route("/generate_api_key", methods=["POST"])
@require_dev_admin
def generate_api_key(db):
    data = request.get_json(silent=True) or {}
    current_key = data.get("current_api_key")
    db_key = get_setting_value(db, "api_key")
    if not current_key or current_key != db_key:
        return jsonify({"success": False, "message": "Current API Key is incorrect or missing."}), 403
    
    new_key = secrets.token_hex(32)
    # validate_settings_changes is bypassed for direct internal update, but we should import update_setting_value
    from backend.models.setting_model import update_setting_value
    update_setting_value(db, "api_key", new_key)
    
    import os
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env"))
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
        with open(env_path, "w") as f:
            for line in lines:
                if line.startswith("VITE_API_KEY="):
                    f.write(f"VITE_API_KEY={new_key}\n")
                else:
                    f.write(line)

    return jsonify({"success": True, "new_api_key": new_key})


@dev_admin_api.route("/machines", methods=["GET"])
@require_dev_admin
def machines(db):
    return jsonify({"success": True, **build_machines_payload(db)})


@dev_admin_api.route("/machines/<machine_name>", methods=["PATCH"])
@require_dev_admin
def update_machine(db, machine_name):
    data = request.get_json(silent=True) or {}
    validated, errors = validate_machine_update(db, machine_name, data)
    if errors:
        return jsonify({"success": False, "message": "Invalid machine update.", "errors": errors}), 400
    try:
        machine = apply_machine_update(db, validated or {})
    except Exception:
        db.rollback()
        raise
    return jsonify({"success": True, "machine": machine})


@dev_admin_api.route("/machine-layout", methods=["PATCH"])
@require_dev_admin
def update_machine_layout(db):
    data = request.get_json(silent=True) or {}
    validated, errors = validate_machine_order(db, data.get("order"))
    if errors:
        return jsonify({"success": False, "message": "Invalid machine layout.", "errors": errors}), 400
    try:
        payload = apply_machine_order(db, validated or {})
    except Exception:
        db.rollback()
        raise
    return jsonify({"success": True, **payload})


@dev_admin_api.route("/export-config", methods=["GET"])
@require_dev_admin
def export_config(db):
    return jsonify({"success": True, **build_export_config(db)})
