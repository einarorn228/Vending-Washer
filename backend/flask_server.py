import base64
import hashlib
import logging
import time
import uuid
from datetime import datetime
from io import StringIO
from typing import Optional

from flask import Flask, Response, g, jsonify, request
from flask_cors import CORS
from backend.controllers.code_generator import generate_new_code
from backend.controllers.ui_api import ui_api
from backend.models import remove_session, session
from backend.models.code_model import Code
from backend.models.scan_log_model import ScanLog
from backend.models.setting_model import get_setting_value, update_setting_value
from backend.services.reisa_audit_service import list_audit_events_for_session
from backend.services.reisa_diagnostics_service import get_reisa_session_diagnostics, get_reisa_sync_diagnostics
from backend.services.reisa_replay_service import replay_due_jobs, replay_retry_job
from backend.services.reisa_retry_service import list_retry_jobs, list_retry_jobs_for_session
from logging import getLogger
import csv

from backend.metrics import inc, observe_ms, snapshot

logger = logging.getLogger(__name__)
root_logger = getLogger()

app = Flask(__name__)

app.register_blueprint(ui_api, url_prefix="/api")


def _load_cors_origins() -> list[str]:
    try:
        allowed_origins = get_setting_value(session, "cors_allowed_origins", "")
    except Exception:
        # Startup/import paths may read this module before DB init/bootstrap.
        return []
    return [o.strip() for o in str(allowed_origins).split(",") if o.strip()]


def configure_flask_runtime(flask_app: Optional[Flask] = None) -> None:
    """Apply runtime-only Flask configuration (safe to call multiple times)."""

    target = flask_app or app
    if getattr(target, "_cors_configured", False):
        return
    CORS(target, origins=_load_cors_origins())
    setattr(target, "_cors_configured", True)


@app.before_request
def _start_timer_and_request_id():
    g._t0 = time.perf_counter()
    g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    g.session_id = request.cookies.get("session_id")


@app.after_request
def _log_request(resp):
    start = getattr(g, "_t0", None)
    if start is None:
        duration_ms = 0
    else:
        duration_ms = int((time.perf_counter() - start) * 1000)

    request_id = getattr(g, "request_id", uuid.uuid4().hex)
    session_id = getattr(g, "session_id", None)
    extra = {
        "request_id": request_id,
        "route": request.path,
        "method": request.method,
        "status": resp.status_code,
        "latency_ms": duration_ms,
        "session_id": session_id,
        "client_ip": request.remote_addr,
    }

    level = logging.INFO if resp.status_code < 400 else logging.ERROR
    root_logger.log(level, "HTTP request", extra=extra)

    inc(
        "http_requests_total",
        endpoint=request.path,
        method=request.method,
        status=resp.status_code,
    )
    observe_ms(
        "http_request_duration_ms",
        duration_ms,
        endpoint=request.path,
    )

    resp.headers["X-Request-ID"] = request_id
    return resp


@app.teardown_appcontext
def _teardown_session(_exception=None):
    remove_session()


def check_admin_auth(auth_header):
    if not auth_header or not auth_header.startswith("Basic "):
        return False
    try:
        b64 = auth_header.split(" ", 1)[1]
        userpass = base64.b64decode(b64).decode("utf-8")
        username, password = userpass.split(":", 1)
    except Exception:
        return False
    db_user = get_setting_value(session, "admin_username")
    db_pass_hash = get_setting_value(session, "admin_password_hash")
    if db_user is None or db_pass_hash is None:
        return False
    pass_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return username == db_user and pass_hash == db_pass_hash


def require_admin_auth(view_function):
    def decorated_function(*args, **kwargs):
        header_key = request.headers.get("X-API-KEY")
        db_key = get_setting_value(session, "api_key")
        if not header_key or header_key != db_key:
            resp = jsonify({"error": "Invalid or missing API key"})
            resp.status_code = 401
            return resp
        auth_header = request.headers.get("Authorization")
        if not check_admin_auth(auth_header):
            resp = jsonify({"error": "Admin authentication required"})
            resp.status_code = 401
            resp.headers["WWW-Authenticate"] = 'Basic realm="Admin Area"'
            return resp
        return view_function(*args, **kwargs)

    decorated_function.__name__ = view_function.__name__
    return decorated_function


def require_api_key(view_function):
    def decorated_function(*args, **kwargs):
        header_key = request.headers.get("X-API-KEY")
        db_key = get_setting_value(session, "api_key")
        if not header_key or header_key != db_key:
            resp = jsonify({"error": "Invalid or missing API key"})
            resp.status_code = 401
            return resp
        return view_function(*args, **kwargs)

    decorated_function.__name__ = view_function.__name__
    return decorated_function


@app.route("/generate_code", methods=["POST"])
@require_api_key
def generate_code():
    """Endpoint to generate a new QR code based on an order ID."""
    try:
        # Parse the request body
        data = request.get_json(force=True)

        # Get data from body
        order_id = data.get("order_id")
        usage_limit = data.get("usage_limit")

        # Error handling
        if not order_id or usage_limit is None:
            return jsonify({"error": "Missing order_id or usage_limit"}), 400

        # Generate the code using the refactored logic
        response = generate_new_code(order_id, usage_limit)
        logger.info("Generated code for order %s", order_id)

        # Provide human friendly expiration info
        exp = response.get("expiration_date")
        if exp is None:
            exp_msg = "Code does not expire while unused."
        else:
            exp_msg = f"Code expires on {exp}."
        response["expiration_message"] = exp_msg

        return jsonify(response), response["status_code"]

    except Exception:
        logger.exception("Failed to process /generate_code request")
        return jsonify({"error": "Failed to process request"}), 400


# ----- Admin/Debug Endpoints -----
# TODO: Add authentication before exposing in production


def _normalise_labels(labels_tuple):
    return {k: v for k, v in labels_tuple}




@app.route("/admin/reisa/retry_jobs", methods=["GET"])
@require_admin_auth
def admin_reisa_retry_jobs():
    limit_raw = request.args.get("limit", "100")
    status = (request.args.get("status", "") or "").strip() or None
    due_only_raw = (request.args.get("due_only", "false") or "").strip().lower()
    due_only = due_only_raw in {"1", "true", "yes", "on"}
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 100
    jobs = list_retry_jobs(limit=limit, status=status, due_only=due_only)
    return jsonify({"limit": max(min(limit, 500), 1), "count": len(jobs), "jobs": jobs})


@app.route("/admin/reisa/session/<session_uid>", methods=["GET"])
@require_admin_auth
def admin_reisa_session_diagnostics(session_uid):
    limit_raw = request.args.get("limit", "100")
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 100
    payload = get_reisa_session_diagnostics(session_uid=session_uid, limit=limit)
    payload["limit"] = max(min(limit, 500), 1)
    return jsonify(payload)


@app.route("/admin/reisa/audit/<session_uid>", methods=["GET"])
@require_admin_auth
def admin_reisa_audit_for_session(session_uid):
    limit_raw = request.args.get("limit", "100")
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 100
    events = list_audit_events_for_session(session_uid=session_uid, limit=limit)
    jobs = list_retry_jobs_for_session(session_uid=session_uid, limit=limit)
    return jsonify(
        {
            "session_uid": session_uid,
            "limit": max(min(limit, 500), 1),
            "audit_events": events,
            "retry_jobs": jobs,
        }
    )


@app.route("/admin/reisa/retry/<int:job_id>", methods=["POST"])
@require_admin_auth
def admin_reisa_retry_job(job_id):
    outcome = replay_retry_job(job_id)
    status_code = 200 if outcome.success else 500
    return (
        jsonify(
            {
                "job_id": job_id,
                "success": outcome.success,
                "status": outcome.status,
                "message": outcome.message,
            }
        ),
        status_code,
    )


@app.route("/admin/reisa/retry_due", methods=["POST"])
@require_admin_auth
def admin_reisa_retry_due_jobs():
    limit_raw = request.args.get("limit", "20")
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 20
    summary = replay_due_jobs(limit=limit)
    summary["limit"] = max(min(limit, 200), 1)
    return jsonify(summary)


@app.route("/admin/reisa/sync_failures", methods=["GET"])
@require_admin_auth
def admin_reisa_sync_failures():
    limit_raw = request.args.get("limit", "100")
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 100
    payload = get_reisa_sync_diagnostics(limit=limit)
    payload["limit"] = max(min(limit, 500), 1)
    return jsonify(payload)

@app.route("/admin/metrics", methods=["GET"])
@require_admin_auth
def admin_metrics():
    counters, gauges, histograms = snapshot()

    def _prepare(mapping):
        return [
            {"name": name, "labels": _normalise_labels(labels), "value": value}
            for (name, labels), value in mapping.items()
        ]

    histo_payload = []
    for (name, labels), values in histograms.items():
        entry = {"name": name, "labels": _normalise_labels(labels)}
        entry.update(values)
        histo_payload.append(entry)

    return jsonify(
        {
            "counters": _prepare(counters),
            "gauges": _prepare(gauges),
            "histograms": histo_payload,
        }
    )


@app.route("/admin/metrics/export.csv", methods=["GET"])
@require_admin_auth
def admin_metrics_export():
    counters, gauges, histograms = snapshot()
    buffer = StringIO()
    writer = csv.writer(buffer)
    timestamp = datetime.utcnow().isoformat()

    writer.writerow(["timestamp", "type", "name", "labels", "metric", "value"])

    def _labels_to_str(labels_tuple):
        labels = _normalise_labels(labels_tuple)
        if not labels:
            return "-"
        return ";".join(f"{k}={v}" for k, v in sorted(labels.items()))

    for (name, labels), value in counters.items():
        writer.writerow([timestamp, "counter", name, _labels_to_str(labels), "value", value])
    for (name, labels), value in gauges.items():
        writer.writerow([timestamp, "gauge", name, _labels_to_str(labels), "value", value])
    histo_metrics = ("count", "avg_ms", "p95_ms", "p99_ms", "max_ms")
    for (name, labels), values in histograms.items():
        for metric_name in histo_metrics:
            metric_value = values.get(metric_name)
            if metric_value is not None:
                writer.writerow(
                    [
                        timestamp,
                        "histogram",
                        name,
                        _labels_to_str(labels),
                        metric_name,
                        metric_value,
                    ]
                )

    csv_data = buffer.getvalue()
    buffer.close()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=metrics_export.csv"},
    )


@app.route("/admin/usage/by_order_id/<order_id>", methods=["GET"])
@require_admin_auth
def get_usage_by_order_id(order_id):
    """Return all scan log entries for the given order ID."""
    logs = (
        session.query(ScanLog)
        .filter(ScanLog.order_id == order_id)
        .order_by(ScanLog.timestamp.desc())
        .all()
    )
    if not logs:
        # Check if the order_id exists in codes
        order_exists = session.query(Code).filter(Code.order_id == order_id).first()
        if order_exists is None:
            return (
                jsonify(
                    {
                        "message": f"No scan logs found for order_id '{order_id}'. Order ID does not exist."
                    }
                ),
                404,
            )
        else:
            return (
                jsonify(
                    {"message": f"Order ID '{order_id}' has not been scanned yet."}
                ),
                404,
            )
    result = [
        {
            "id": log.id,
            "code": log.code,
            "order_id": log.order_id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "result": log.result,
            "details": log.details,
        }
        for log in logs
    ]
    return jsonify(result)


@app.route("/admin/usage/by_code/<code>", methods=["GET"])
@require_admin_auth
def get_usage_by_code(code):
    """Return all scan log entries for the given code."""
    logs = (
        session.query(ScanLog)
        .filter(ScanLog.code == code)
        .order_by(ScanLog.timestamp.desc())
        .all()
    )
    if not logs:
        # Check if the code exists in codes
        code_exists = session.query(Code).filter(Code.code == code).first()
        if code_exists is None:
            return (
                jsonify(
                    {
                        "message": f"No scan logs found for code '{code}'. Code does not exist."
                    }
                ),
                404,
            )
        else:
            return jsonify({"message": f"Code '{code}' has not been scanned yet."}), 404
    result = [
        {
            "id": log.id,
            "code": log.code,
            "order_id": log.order_id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "result": log.result,
            "details": log.details,
        }
        for log in logs
    ]
    return jsonify(result)


@app.route("/admin/scan_logs/last/<int:count>", methods=["GET"])
@require_admin_auth
def get_last_scan_logs(count):
    """Return the last `count` scan log entries."""
    logs = session.query(ScanLog).order_by(ScanLog.timestamp.desc()).limit(count).all()
    if not logs:
        return jsonify({"message": "No scan logs found."}), 404
    result = [
        {
            "id": log.id,
            "code": log.code,
            "order_id": log.order_id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "result": log.result,
            "details": log.details,
        }
        for log in logs
    ]
    return jsonify(result)


def serialize_code(code_obj):
    """Serialize a Code row with usage information."""
    usage_left = (code_obj.usage_limit or 0) - (code_obj.current_usage or 0)
    data = {
        "code": code_obj.code,
        "order_id": code_obj.order_id,
        "usage_limit": code_obj.usage_limit,
        "current_usage": code_obj.current_usage,
        "usage_left": usage_left,
    }
    # Include optional fields if present on the model
    if hasattr(code_obj, "expiration_date"):
        data["expiration_date"] = (
            code_obj.expiration_date.isoformat() if code_obj.expiration_date else None
        )
    if hasattr(code_obj, "created_at"):
        data["created_at"] = (
            code_obj.created_at.isoformat() if code_obj.created_at else None
        )
    if usage_left <= 0:
        data["status"] = "expired"
    return data


# ----- QR Code Admin/Debug Endpoints -----
# These endpoints are meant for debugging and admin use.


@app.route("/admin/codes", methods=["GET"])
@require_admin_auth
def get_all_codes():
    """Return all QR codes in the database."""
    codes = session.query(Code).order_by(Code.code).all()
    if not codes:
        return jsonify({"message": "No codes found."}), 404
    return jsonify([serialize_code(c) for c in codes])


@app.route("/admin/codes/last/<int:count>", methods=["GET"])
@require_admin_auth
def get_last_codes(count):
    """Return the last ``count`` created codes."""
    query = session.query(Code)
    if hasattr(Code, "created_at"):
        query = query.order_by(Code.created_at.desc())
    else:
        query = query.order_by(Code.code.desc())
    codes = query.limit(count).all()
    if not codes:
        return jsonify({"message": "No codes found."}), 404
    return jsonify([serialize_code(c) for c in codes])


@app.route("/admin/codes/by_order_id/<order_id>", methods=["GET"])
@require_admin_auth
def get_codes_by_order_id(order_id):
    """Return all codes associated with the given order ID."""
    codes = (
        session.query(Code).filter(Code.order_id == order_id).order_by(Code.code).all()
    )
    if not codes:
        # Check if the order_id exists at all
        order_exists = session.query(Code).filter(Code.order_id == order_id).first()
        if order_exists is None:
            return (
                jsonify(
                    {
                        "message": f"No codes found for order_id '{order_id}'. Order ID does not exist."
                    }
                ),
                404,
            )
        else:
            return (
                jsonify({"message": f"No codes found for order_id '{order_id}'."}),
                404,
            )
    return jsonify([serialize_code(c) for c in codes])


@app.route("/admin/codes/<code>", methods=["GET"])
@require_admin_auth
def get_code_info(code):
    """Return info about a specific code."""
    code_obj = session.query(Code).filter(Code.code == code).first()
    if not code_obj:
        return jsonify({"message": f"Code '{code}' does not exist."}), 404
    return jsonify(serialize_code(code_obj))


@app.route("/admin/codes/<code>", methods=["DELETE"])
@require_admin_auth
def delete_code_by_code(code):
    """Delete a code by its code value."""
    code_obj = session.query(Code).filter(Code.code == code).first()
    if not code_obj:
        return jsonify({"message": f"Code '{code}' does not exist."}), 404
    session.delete(code_obj)
    session.commit()
    return jsonify({"message": f"Code '{code}' deleted."}), 200


@app.route("/admin/codes/by_order_id/<order_id>", methods=["DELETE"])
@require_admin_auth
def delete_codes_by_order_id(order_id):
    """Delete all codes associated with a given order ID."""
    codes = session.query(Code).filter(Code.order_id == order_id).all()
    if not codes:
        return jsonify({"message": f"No codes found for order_id '{order_id}'."}), 404
    count = len(codes)
    for code in codes:
        session.delete(code)
    session.commit()
    return (
        jsonify({"message": f"Deleted {count} code(s) for order_id '{order_id}'."}),
        200,
    )


@app.route("/admin/settings/cors", methods=["PUT"])
@require_admin_auth
def update_cors():
    """Update allowed CORS origins."""
    data = request.get_json(force=True)
    origins = data.get("origins")
    if origins is None:
        return jsonify({"error": "Missing origins"}), 400
    if isinstance(origins, list):
        origins = ",".join(origins)
    update_setting_value(session, "cors_allowed_origins", origins)
    return jsonify({"message": "CORS origins updated"})


@app.route("/admin/settings/<key>", methods=["GET", "PUT"])
@require_admin_auth
def manage_setting(key):
    """Retrieve or update an arbitrary setting."""
    if request.method == "GET":
        value = get_setting_value(session, key)
        if value is None:
            return jsonify({"error": "Setting not found"}), 404
        return jsonify({"key": key, "value": value})

    data = request.get_json(force=True)
    value = data.get("value")
    if value is None:
        return jsonify({"error": "Missing value"}), 400
    update_setting_value(session, key, value)
    return jsonify({"message": "Setting updated", "key": key, "value": value})
