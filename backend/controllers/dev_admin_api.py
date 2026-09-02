"""Temporary beta/dev admin API.

This blueprint is intentionally protected by a backend kill switch and API-key
check, then narrowed further by service-layer whitelists. It is not a production
admin system.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import threading
from functools import wraps

from flask import Blueprint, jsonify, request


from backend.metrics import inc
from backend.utils.runtime_env import running_under_tests
from backend.models import Session
from backend.models.setting_model import (
    get_setting_value,
    parse_setting_bool,
    stage_setting_value,
)
from backend.models.settings_audit_model import ENTITY_SETTING, redact_audit_value
from backend.services.diagnostics_service import metrics_snapshot, recent_scan_logs
from backend.services.dev_admin_service import (
    LOCKOUT_CONFIRMATION_PHRASE,
    apply_machine_order,
    apply_machine_update,
    apply_machine_updates,
    apply_settings_changes,
    read_audit_entries,
    record_audit_entry,
    build_export_config,
    build_grouped_settings,
    build_machines_payload,
    build_status,
    validate_machine_order,
    validate_machine_update,
    validate_machine_updates,
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

    # Disabling the panel is a one-way door from the browser's point of view, so it
    # requires an explicit typed phrase and cannot ride along with a bulk save.
    if "dev_admin_enabled" in changes and not parse_setting_bool(
        changes["dev_admin_enabled"], default=True
    ):
        supplied = str(data.get("confirmation_phrase") or "").strip()
        if supplied != LOCKOUT_CONFIRMATION_PHRASE:
            return jsonify({
                "success": False,
                "message": (
                    "Disabling the dev/admin panel locks this browser out. "
                    f"Send confirmation_phrase=\"{LOCKOUT_CONFIRMATION_PHRASE}\" to proceed."
                ),
                "requires_confirmation": "dev_admin_enabled",
                "confirmation_phrase": LOCKOUT_CONFIRMATION_PHRASE,
                "errors": {},
            }), 400

    validated, errors = validate_settings_changes(db, changes)
    if errors:
        return jsonify({"success": False, "message": "Invalid settings update.", "errors": errors}), 400
    try:
        # Stage everything, then commit once, so a failure in the secret writes
        # cannot leave the whitelisted changes already applied.
        updated = apply_settings_changes(db, validated or {}, commit=False)

        for skey, sval in sensitive_updates.items():
            previous = get_setting_value(db, skey)
            stage_setting_value(db, skey, str(sval))
            # Secrets are audited by presence only, never by value.
            record_audit_entry(
                db,
                entity_type=ENTITY_SETTING,
                entity_key=skey,
                field=skey,
                old_value=redact_audit_value(previous),
                new_value=redact_audit_value(sval),
                is_high_risk=True,
            )
            updated.append({"key": skey, "value": "***", "restart_required": False})

        db.commit()
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
    try:
        stage_setting_value(db, "api_key", new_key)
        record_audit_entry(
            db,
            entity_type=ENTITY_SETTING,
            entity_key="api_key",
            field="api_key",
            old_value=redact_audit_value(db_key),
            new_value=redact_audit_value(new_key),
            is_high_risk=True,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    def update_env():
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
                        
    # Wait 1.5 seconds before updating .env so the JSON response reaches the frontend.
    # Never rewrite the developer's real frontend/.env from a test run: the path is
    # anchored to __file__, so it points at the repository copy regardless of cwd or
    # database isolation.
    if not running_under_tests():
        threading.Timer(1.5, update_env).start()

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


@dev_admin_api.route("/machines", methods=["PATCH"])
@require_dev_admin
def update_machines(db):
    """Save every changed machine card, and the display order, as one transaction.

    The per-machine PATCH above stays for single edits; the panel's Save uses this
    so a rejected row cannot leave the earlier machines already written.
    """

    data = request.get_json(silent=True) or {}
    validated, errors = validate_machine_updates(db, data.get("updates"))
    if errors:
        return jsonify({
            "success": False,
            "message": "No machines were saved. Fix the errors and save again.",
            "errors": errors,
        }), 400

    order = data.get("order")
    if order is not None:
        order_validated, order_errors = validate_machine_order(db, order)
        if order_errors:
            return jsonify({
                "success": False,
                "message": "No machines were saved. Fix the errors and save again.",
                "errors": {"order": order_errors},
            }), 400
        order = order_validated["order"]

    try:
        payload = apply_machine_updates(db, validated or [], order)
    except Exception:
        db.rollback()
        raise
    return jsonify({"success": True, **payload})


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


@dev_admin_api.route("/telemetry", methods=["GET"])
@require_dev_admin
def telemetry(db):
    """Live per-machine readings and thresholds, for tuning on_/off_threshold."""

    from backend.controllers.telemetry import MachineStateStore

    return jsonify({
        "success": True,
        "telemetry_enabled": parse_setting_bool(
            get_setting_value(db, "telemetry_enabled", default="true"), default=True
        ),
        "machines": MachineStateStore.instance().get_diagnostic_snapshot(),
    })


@dev_admin_api.route("/diagnostics", methods=["GET"])
@require_dev_admin
def diagnostics(db):
    """Recent scan logs, runtime metrics, and the configuration audit trail."""

    limit = request.args.get("limit", default=50, type=int) or 50
    return jsonify({
        "success": True,
        "scan_logs": recent_scan_logs(db, limit),
        "metrics": metrics_snapshot(),
        "audit_log": read_audit_entries(db, limit=100),
    })


@dev_admin_api.route("/kiosk_state", methods=["GET"])
@require_dev_admin
def kiosk_state(db):
    from backend.controllers.machine_control import UI_STATE, get_machine_snapshot

    state = dict(UI_STATE)
    state["machines"] = get_machine_snapshot()
    return jsonify({"success": True, "kiosk_state": state})


@dev_admin_api.route("/remote_scan", methods=["POST"])
@require_dev_admin
def remote_scan(db):
    from backend.services.start_orchestrator import SCAN_BUSY_MESSAGE, ingest_scan

    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    if not code:
        return _json_error("Missing code", 400)
    outcome = ingest_scan(code, source="dev_admin")
    if not outcome.success:
        status = 409 if outcome.message == SCAN_BUSY_MESSAGE else 400
        return jsonify({"success": False, "message": outcome.message}), status
    code_info = outcome.code_info
    uses_left = code_info.usage_limit - code_info.current_usage if code_info else None
    return jsonify({"success": True, "message": outcome.message, "uses_left": uses_left})


@dev_admin_api.route("/remote_touch_select", methods=["POST"])
@require_dev_admin
def remote_touch_select(db):
    from backend.services.start_orchestrator import start_from_touch

    data = request.get_json(silent=True) or {}
    machine_id = (data.get("machine_id") or "").strip()
    if not machine_id:
        return _json_error("Missing machine_id", 400)
    outcome = start_from_touch(machine_id=machine_id)
    status = 200 if outcome.success else 409
    return jsonify({"success": outcome.success, "message": outcome.message, "uses_left": outcome.uses_left}), status


@dev_admin_api.route("/remote_reset", methods=["POST"])
@require_dev_admin
def remote_reset(db):
    from backend.controllers.machine_control import update_ui_state

    update_ui_state({
        "state": "waiting_for_code",
        "message": "Scan your code to start",
        "current_machine": None,
        "uses_left": None,
    })
    return jsonify({"success": True, "message": "Kiosk reset to ready state."})
