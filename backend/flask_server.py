import logging
import base64
import hashlib
from flask import Flask, jsonify, request
from flask_cors import CORS
from controllers.code_generator import generate_new_code
from controllers.ui_api import ui_api
from models import session
from models.scan_log_model import ScanLog
from models.code_model import Code
from models.setting_model import get_setting_value, update_setting_value

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure dynamic CORS based on allowed origins stored in the DB
allowed_origins = get_setting_value(session, "cors_allowed_origins", "")
origins_list = [o.strip() for o in allowed_origins.split(",") if o.strip()]
CORS(app, origins=origins_list)

app.register_blueprint(ui_api, url_prefix="/api")


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
def delete_code_by_code(code):
    """Delete a code by its code value."""
    code_obj = session.query(Code).filter(Code.code == code).first()
    if not code_obj:
        return jsonify({"message": f"Code '{code}' does not exist."}), 404
    session.delete(code_obj)
    session.commit()
    return jsonify({"message": f"Code '{code}' deleted."}), 200


@app.route("/admin/codes/by_order_id/<order_id>", methods=["DELETE"])
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
