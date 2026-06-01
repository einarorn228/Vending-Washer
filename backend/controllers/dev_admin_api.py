"""Temporary beta/dev admin API.

This blueprint is intentionally protected by a backend kill switch and API-key
check, then narrowed further by service-layer whitelists. It is not a production
admin system.
"""

from __future__ import annotations

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


def _valid_api_key(db) -> bool:
    key = request.headers.get(API_KEY_HEADER) or request.args.get("api_key")
    db_key = get_setting_value(db, "api_key")
    return bool(key and db_key and key == db_key)


def require_dev_admin(view_function):
    @wraps(view_function)
    def decorated(*args, **kwargs):
        db = Session()
        try:
            if not _is_enabled(db):
                return _json_error(DEV_ADMIN_DISABLED_MESSAGE, 403, disabled=True)
            if not _valid_api_key(db):
                inc("http_auth_failures", endpoint=request.path or "dev_admin")
                return _json_error("Invalid API key", 401)
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
    validated, errors = validate_settings_changes(db, data.get("changes"))
    if errors:
        return jsonify({"success": False, "message": "Invalid settings update.", "errors": errors}), 400
    try:
        updated = apply_settings_changes(db, validated or {})
    except Exception:
        db.rollback()
        raise
    return jsonify({"success": True, "updated": updated, "errors": {}})


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
