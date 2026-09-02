"""Service helpers for the temporary beta dev/admin API.

The functions in this module intentionally use whitelists and validate complete
payloads before applying any writes. This keeps route handlers small and avoids
arbitrary settings or machine database writes.
"""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Any, Dict, Mapping, Optional, Tuple

from sqlalchemy.orm import joinedload

from backend.controllers import machine_control
from backend.controllers import qr_scanner
from backend.models.device_model import Device
from backend.models.machine_model import Machine, MachineConfig
from backend.models.setting_model import Settings, get_setting_value, parse_setting_bool
from backend.models.settings_audit_model import (
    ENTITY_MACHINE,
    ENTITY_SETTING,
    SettingsAuditLog,
    serialize_audit_entry,
)
from backend.services.machine_layout_service import (
    MACHINE_CARD_LAYOUT_KEY,
    default_short_label,
    infer_machine_type,
    load_machine_card_layout,
    machine_layout_entry,
    serialize_machine_card_layout,
)

SECRET_KEYS = {"api_key", "admin_password_hash", "reisa_bearer_token"}

# Turning the panel off locks every admin out of /dev/admin until someone edits the
# database over SSH, so it must not be reachable by an ordinary settings save.
LOCKOUT_CONFIRMATION_PHRASE = "DISABLE DEV ADMIN"
BOOL_TRUE = {"1", "true", "yes", "on"}
BOOL_FALSE = {"0", "false", "no", "off"}

SETTING_GROUPS = [
    {"id": "dev_admin", "title": "Dev/Admin Access"},
    {"id": "api_security", "title": "API / Security"},
    {"id": "scanner", "title": "Scanner"},
    {"id": "machine_timing", "title": "Machine Timing"},
    {"id": "screen_timing", "title": "Screen Timing"},
    {"id": "hardware_timing", "title": "Hardware Timing"},
    {"id": "kiosk", "title": "Kiosk Input"},
    {"id": "runtime", "title": "Shelly / Runtime Toggles"},
    {"id": "codes", "title": "Codes"},
    {"id": "provider", "title": "Provider / Mode"},
    {"id": "logging", "title": "Logging / Diagnostics"},
]

SETTING_SCHEMA: Dict[str, Dict[str, Any]] = {
    "dev_admin_enabled": {
        "group": "dev_admin",
        "label": "Beta dev/admin enabled",
        "type": "bool",
        "default": "false",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "description": "Backend kill switch for this temporary beta/dev admin panel.",
    },
    "api_key": {
        "group": "api_security",
        "label": "API key",
        "type": "secret",
        "editable": False,
        "restart_required": False,
        "risk": "high",
        "description": "Used as the temporary dev/admin password. Raw value is never shown here.",
    },
    "admin_username": {
        "group": "api_security",
        "label": "Admin username",
        "type": "string",
        "editable": False,
        "restart_required": False,
        "risk": "high",
        "description": "Existing Basic-auth admin username. Read-only in the first beta panel.",
    },
    "admin_password_hash": {
        "group": "api_security",
        "label": "Admin password hash",
        "type": "secret",
        "editable": False,
        "restart_required": False,
        "risk": "high",
        "description": "Existing admin password hash. Raw value is never shown or edited here.",
    },
    "cors_allowed_origins": {
        "group": "api_security",
        "label": "CORS allowed origins",
        "type": "list",
        "editable": True,
        "restart_required": True,
        "risk": "high",
        "description": "Comma-separated/list of browser origins allowed by Flask CORS. Restart likely required.",
    },
    "serial_port": {
        "group": "scanner",
        "label": "Serial port",
        "type": "string",
        "default": "/dev/ttyACM0",
        "editable": True,
        "restart_required": True,
        "risk": "medium",
        "description": "USB serial device path for the QR scanner. Restart scanner/backend after changes.",
    },
    "serial_baudrate": {
        "group": "scanner",
        "label": "Serial baud rate",
        "type": "int",
        "default": "9600",
        "editable": True,
        "restart_required": True,
        "risk": "medium",
        "min": 1200,
        "max": 115200,
        "description": "Scanner serial baud rate. Restart scanner/backend after changes.",
    },
    "scan_timeout": {
        "group": "scanner",
        "label": "Scan timeout",
        "type": "float",
        "default": "3",
        "editable": True,
        "restart_required": True,
        "risk": "medium",
        "min": 0.1,
        "max": 30,
        "description": "Serial read timeout used when opening the scanner. Restart scanner/backend after changes.",
    },
    "button_select_timeout_sec": {
        "group": "machine_timing",
        "label": "Button selection timeout (seconds)",
        "type": "int",
        "default": "45",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "min": 5,
        "max": 300,
        "description": "How long a scanned code remains armed for physical button-box selection.",
    },
    "machine_reservation_minutes": {
        "group": "machine_timing",
        "label": "Machine reservation duration (minutes)",
        "type": "int",
        "default": "10",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "min": 1,
        "max": 120,
        "description": "How long the machine is reserved after the user selects it before it becomes available again.",
    },
    "backend_relay_enabled": {
        "group": "runtime",
        "label": "Backend relay control enabled",
        "type": "bool",
        "default": "false",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "description": "When enabled, backend can send real Shelly relay commands.",
    },
    "telemetry_enabled": {
        "group": "runtime",
        "label": "Telemetry polling enabled",
        "type": "bool",
        "default": "true",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "description": "Controls Shelly telemetry HTTP polling loop behavior.",
    },
    "button_box_enabled": {
        "group": "runtime",
        "label": "Button box input enabled",
        "type": "bool",
        "default": "false",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "description": "Allows physical I4/button-box input as a secondary machine-selection source.",
    },
    "provider_default": {
        "group": "provider",
        "label": "Default provider",
        "type": "enum",
        "choices": ["local", "reisa"],
        "default": "local",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "description": "Changes scan/start semantics. Reisa requires its provider gate and secrets to be configured.",
    },
    "provider_reisa_enabled": {
        "group": "provider",
        "label": "Reisa provider enabled",
        "type": "bool",
        "default": "false",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "description": "Allows provider_default=reisa to use the Reisa integration.",
    },
    "reisa_base_url": {
        "group": "provider",
        "label": "Reisa base URL",
        "type": "string",
        "default": "",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "description": "Base URL for Reisa provider calls. Token remains read-only/masked in this beta.",
    },
    "reisa_bearer_token": {
        "group": "provider",
        "label": "Reisa bearer token",
        "type": "secret",
        "editable": False,
        "restart_required": False,
        "risk": "high",
        "description": "Secret token. Raw value is never shown or edited here.",
    },
    "kiosk_input_mode": {
        "group": "kiosk",
        "label": "Kiosk input mode (legacy)",
        "type": "enum",
        "choices": ["touch", "hardware_buttons"],
        "default": "hardware_buttons",
        "editable": False,
        "restart_required": False,
        "risk": "low",
        "description": "Legacy metadata echoed on /api/ui_state as input_mode. It has no runtime effect today - touch machine selection is always allowed. Use 'Button box input enabled' to control the physical button box.",
    },
    "code_expiration_days": {
        "group": "codes",
        "label": "Code expiration (days)",
        "type": "int",
        "default": "0",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "min": 0,
        "max": 3650,
        "description": "Days until a newly generated local code expires. 0 means codes never expire. Only affects codes created after the change.",
    },
    "selection_notice_seconds": {
        "group": "screen_timing",
        "label": "Machine-selected notice (seconds)",
        "type": "float",
        "default": "3.0",
        "editable": True,
        "restart_required": False,
        "risk": "low",
        "min": 0.5,
        "max": 30,
        "description": "How long the kiosk shows the 'machine starting' screen before returning to the ready screen if telemetry never confirms.",
    },
    "started_notice_seconds": {
        "group": "screen_timing",
        "label": "Machine-started notice (seconds)",
        "type": "float",
        "default": "3.0",
        "editable": True,
        "restart_required": False,
        "risk": "low",
        "min": 0.5,
        "max": 30,
        "description": "How long the confirmation screen stays up after a run is confirmed, before the kiosk resets to ready.",
    },
    "error_notice_seconds": {
        "group": "screen_timing",
        "label": "Error notice (seconds)",
        "type": "float",
        "default": "3.0",
        "editable": True,
        "restart_required": False,
        "risk": "low",
        "min": 1,
        "max": 30,
        "description": "How long an error message stays on the kiosk screen before it auto-resets to ready.",
    },
    "kiosk_poll_interval_ms": {
        "group": "screen_timing",
        "label": "Kiosk poll interval (ms)",
        "type": "int",
        "default": "1000",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "min": 250,
        "max": 10000,
        "description": "How often the kiosk screen asks the backend for the current state. Lower feels snappier but adds load; higher is calmer but laggier.",
    },
    "relay_pulse_duration_sec": {
        "group": "hardware_timing",
        "label": "Relay pulse duration (seconds)",
        "type": "float",
        "default": "1.0",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "min": 0.1,
        "max": 10,
        "description": "How long a pulsed Shelly relay stays closed. Machines that ignore a short pulse may need a longer one.",
    },
    "shelly_http_timeout_sec": {
        "group": "hardware_timing",
        "label": "Shelly command timeout (seconds)",
        "type": "float",
        "default": "3.0",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "min": 1,
        "max": 15,
        "description": "How long the backend waits for a Shelly relay command to respond before treating it as failed.",
    },
    "telemetry_http_timeout_sec": {
        "group": "hardware_timing",
        "label": "Telemetry read timeout (seconds)",
        "type": "float",
        "default": "5.0",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "min": 1,
        "max": 30,
        "description": "How long a single telemetry read from a Shelly device may take before it counts as a failed read. Raise it on a noisy Wi-Fi network.",
    },
    "reisa_connect_timeout_ms": {
        "group": "provider",
        "label": "Reisa connect timeout (ms)",
        "type": "int",
        "default": "1500",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "min": 200,
        "max": 30000,
        "description": "How long to wait while opening a connection to Reisa. Too low causes false network timeouts.",
    },
    "reisa_read_timeout_ms": {
        "group": "provider",
        "label": "Reisa read timeout (ms)",
        "type": "int",
        "default": "2500",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "min": 200,
        "max": 60000,
        "description": "How long to wait for a Reisa response once connected. Tune against real provider latency.",
    },
    "reisa_action_start": {
        "group": "provider",
        "label": "Reisa start action",
        "type": "string",
        "default": "WASHING_MACHINE_START",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "description": "Action string sent to Reisa when a machine starts. A wrong value makes Reisa reject every start.",
    },
    "reisa_action_completion": {
        "group": "provider",
        "label": "Reisa completion action",
        "type": "string",
        "default": "WASHING_MACHINE_COMPLETE",
        "editable": True,
        "restart_required": False,
        "risk": "high",
        "description": "Action string sent to Reisa when a run finishes. A wrong value makes Reisa reject every completion.",
    },
    "reisa_retry_worker_enabled": {
        "group": "provider",
        "label": "Reisa retry worker enabled",
        "type": "bool",
        "default": "false",
        "editable": True,
        "restart_required": False,
        "risk": "medium",
        "description": "When on, a background worker retries Reisa calls that failed with a retryable error.",
    },
    "reisa_retry_worker_interval_sec": {
        "group": "provider",
        "label": "Reisa retry interval (seconds)",
        "type": "int",
        "default": "30",
        "editable": True,
        "restart_required": False,
        "risk": "low",
        "min": 5,
        "max": 300,
        "description": "How often the Reisa retry worker looks for due jobs.",
    },
    "reisa_retry_worker_batch_size": {
        "group": "provider",
        "label": "Reisa retry batch size",
        "type": "int",
        "default": "20",
        "editable": True,
        "restart_required": False,
        "risk": "low",
        "min": 1,
        "max": 100,
        "description": "How many Reisa retry jobs are processed in one pass.",
    },
    "log_level": {
        "group": "logging",
        "label": "Log level",
        "type": "enum",
        "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "default": "INFO",
        "editable": True,
        "restart_required": True,
        "risk": "medium",
        "description": "Runtime logger reads this during logger configuration; restart recommended.",
    },
}

MACHINE_TECH_FIELDS = {
    "shelly_ip",
    "relay_channel",
    "i4_button_index",
    "metric_source",
    "on_threshold",
    "off_threshold",
    "on_confirm_ms",
    "off_confirm_ms",
    "poll_interval_ms",
}
METRIC_SOURCES = {"none", "voltage", "power", "digital", "pulse"}
_HOST_RE = re.compile(r"^[A-Za-z0-9.-]+$")


def bool_setting_enabled(db, key: str, default: bool = False) -> bool:
    return parse_setting_bool(get_setting_value(db, key, default="true" if default else "false"), default=default)


def build_status(db) -> dict:
    machines_total = db.query(Machine).count()
    active = db.query(Machine).filter(Machine.is_enabled == 1).count()
    return {
        "dev_admin_enabled": bool_setting_enabled(db, "dev_admin_enabled", default=False),
        "backend_reachable": True,
        "app_mode": {
            "provider_default": get_setting_value(db, "provider_default", default="local"),
            "provider_reisa_enabled": bool_setting_enabled(db, "provider_reisa_enabled", default=False),
        },
        "scanner": scanner_status(db),
        "machines": {"configured": machines_total, "active_in_kiosk": active},
        "runtime": {
            "ui_state": machine_control.UI_STATE.get("state"),
            "button_box_enabled": bool_setting_enabled(db, "button_box_enabled", default=False),
            "backend_relay_enabled": bool_setting_enabled(db, "backend_relay_enabled", default=False),
            "telemetry_enabled": bool_setting_enabled(db, "telemetry_enabled", default=True),
        },
        "settings_loaded_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }


def scanner_status(db) -> dict:
    return {
        "serial_available": bool(getattr(qr_scanner, "SERIAL_AVAILABLE", False)),
        "serial_port": get_setting_value(db, "serial_port", default=getattr(qr_scanner, "SERIAL_PORT", "/dev/ttyACM0")),
        "serial_baudrate": _safe_int(get_setting_value(db, "serial_baudrate", default=getattr(qr_scanner, "SERIAL_BAUDRATE", 9600)), 9600),
        "scan_timeout": _safe_float(get_setting_value(db, "scan_timeout", default=getattr(qr_scanner, "SCAN_TIMEOUT", 3)), 3),
        "restart_required_for_changes": True,
    }


def build_grouped_settings(db) -> dict:
    grouped = []
    for group in SETTING_GROUPS:
        items = []
        for key, schema in SETTING_SCHEMA.items():
            if schema["group"] != group["id"]:
                continue
            items.append(_setting_payload(db, key, schema))
        grouped.append({**group, "settings": items})
    return {"groups": grouped}


def _setting_payload(db, key: str, schema: Mapping[str, Any]) -> dict:
    raw = get_setting_value(db, key, default=schema.get("default", ""))
    payload = {
        "key": key,
        "label": schema["label"],
        "type": schema["type"],
        "editable": bool(schema.get("editable", False)),
        "restart_required": bool(schema.get("restart_required", False)),
        "risk": schema.get("risk", "low"),
        "description": schema.get("description", ""),
        "default": schema.get("default"),
    }
    if "choices" in schema:
        payload["choices"] = schema["choices"]
    if schema["type"] == "secret" or key in SECRET_KEYS:
        payload["value"] = None
        payload["is_set"] = raw is not None and str(raw) != ""
    else:
        payload["value"] = parse_stored_value(raw, schema)
    return payload


def parse_stored_value(raw: Any, schema: Mapping[str, Any]) -> Any:
    value_type = schema.get("type")
    if value_type == "bool":
        return _parse_bool(raw, default=_parse_bool(schema.get("default", "false"), default=False))[0]
    if value_type == "int":
        return _safe_int(raw, _safe_int(schema.get("default"), 0))
    if value_type == "float":
        return _safe_float(raw, _safe_float(schema.get("default"), 0.0))
    if value_type == "list":
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        return [item.strip() for item in str(raw or "").split(",") if item.strip()]
    return "" if raw is None else str(raw)


def validate_settings_changes(db, changes: Mapping[str, Any]) -> Tuple[Optional[dict], Dict[str, str]]:
    if not isinstance(changes, Mapping):
        return None, {"changes": "Expected object of setting changes."}
    validated = {}
    errors = {}
    for key, value in changes.items():
        schema = SETTING_SCHEMA.get(key)
        if not schema:
            errors[key] = "Unknown or unsupported setting."
            continue
        if not schema.get("editable") or schema.get("type") == "secret" or key in SECRET_KEYS:
            errors[key] = "This setting is read-only in the beta dev/admin panel."
            continue
        stored, error = _validate_setting_value(value, schema)
        if error:
            errors[key] = error
        else:
            validated[key] = stored
    return (validated if not errors else None), errors


def record_audit_entry(
    db,
    *,
    entity_type: str,
    entity_key: str,
    field: str,
    old_value,
    new_value,
    is_high_risk: bool = False,
    restart_required: bool = False,
    source: str = "dev_admin",
) -> None:
    """Stage one audit row. Never commits: it rides the caller's transaction."""

    db.add(
        SettingsAuditLog(
            source=source,
            entity_type=entity_type,
            entity_key=entity_key,
            field=field,
            old_value=None if old_value is None else str(old_value),
            new_value=None if new_value is None else str(new_value),
            is_high_risk=bool(is_high_risk),
            restart_required=bool(restart_required),
        )
    )


def read_audit_entries(db, limit: int = 100) -> list:
    limit = max(1, min(int(limit or 100), 500))
    rows = (
        db.query(SettingsAuditLog)
        .order_by(SettingsAuditLog.created_at.desc(), SettingsAuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return [serialize_audit_entry(row) for row in rows]


def apply_settings_changes(db, validated: Mapping[str, str], commit: bool = True) -> list:
    """Stage validated setting writes.

    Pass ``commit=False`` when the caller needs to bundle further writes (for
    example secret updates) into the same transaction.
    """

    updated = []
    for key, stored in validated.items():
        setting = db.query(Settings).filter_by(key=key).first()
        previous = setting.value if setting else None
        if setting:
            setting.value = stored
        else:
            setting = Settings(key=key, value=stored)
            db.add(setting)
        schema = SETTING_SCHEMA[key]
        if previous != stored:
            record_audit_entry(
                db,
                entity_type=ENTITY_SETTING,
                entity_key=key,
                field=key,
                old_value=previous,
                new_value=stored,
                is_high_risk=schema.get("risk") == "high",
                restart_required=bool(schema.get("restart_required", False)),
            )
        updated.append({
            "key": key,
            "value": parse_stored_value(stored, schema),
            "stored_value": stored,
            "restart_required": bool(schema.get("restart_required", False)),
        })
    if commit:
        db.commit()
    return updated


def _validate_setting_value(value: Any, schema: Mapping[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    value_type = schema.get("type")
    if value_type == "bool":
        parsed, ok = _parse_bool(value)
        if not ok:
            return None, "Expected boolean value."
        return "true" if parsed else "false", None
    if value_type == "int":
        parsed, ok = _parse_int(value)
        if not ok:
            return None, "Expected integer value."
        error = _range_error(parsed, schema)
        return (None, error) if error else (str(parsed), None)
    if value_type == "float":
        parsed, ok = _parse_float(value)
        if not ok:
            return None, "Expected numeric value."
        error = _range_error(parsed, schema)
        return (None, error) if error else (str(parsed), None)
    if value_type == "enum":
        text = str(value).strip()
        if text not in schema.get("choices", []):
            return None, f"Expected one of: {', '.join(schema.get('choices', []))}."
        return text, None
    if value_type == "list":
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            items = [item.strip() for item in str(value or "").split(",") if item.strip()]
        return ",".join(items), None
    text = str(value or "").strip()
    if len(text) > schema.get("max_length", 512):
        return None, "Value is too long."
    return text, None


def build_machines_payload(db) -> dict:
    machines = _query_machines(db)
    layout = load_machine_card_layout(db)
    payload = []
    for index, machine in enumerate(machines, start=1):
        payload.append(_machine_payload(machine, layout, index))
    payload.sort(key=lambda item: (item["display_order"], item["display_name"], item["machine_key"]))
    return {"machines": payload}


def _query_machines(db):
    return (
        db.query(Machine)
        .options(joinedload(Machine.uni_device), joinedload(Machine.i4_device), joinedload(Machine.config))
        .order_by(Machine.id.asc())
        .all()
    )


def _machine_payload(machine: Machine, layout: Mapping[str, Any], fallback_order: int) -> dict:
    entry = machine_layout_entry(layout, machine.name, machine.ui_name, fallback_order)
    config = machine.config
    uni_device = machine.uni_device
    return {
        "id": machine.id,
        "machine_key": machine.name,
        "display_name": machine.ui_name,
        "short_label": entry["short_label"],
        "type": entry["type"],
        "display_order": entry["display_order"],
        "active_in_kiosk": bool(machine.is_enabled),
        "description": entry["description"],
        "available": _runtime_available(machine.name),
        "technical": {
            "uni_device_id": machine.uni_device_id,
            "uni_device_name": uni_device.name if uni_device else None,
            "shelly_ip": uni_device.ip if uni_device else None,
            "relay_channel": machine.uni_relay_channel,
            "device_relay_channel": uni_device.relay_channel if uni_device else None,
            "i4_device_id": machine.i4_device_id,
            "i4_device_name": machine.i4_device.name if machine.i4_device else None,
            "i4_button_index": machine.i4_button_index,
            "metric_source": uni_device.metric_source if uni_device else None,
            "on_threshold": config.on_threshold if config else None,
            "off_threshold": config.off_threshold if config else None,
            "on_confirm_ms": config.on_confirm_ms if config else None,
            "off_confirm_ms": config.off_confirm_ms if config else None,
            "poll_interval_ms": config.poll_interval_ms if config else None,
        },
        "field_metadata": {
            "machine_key": {"editable": False},
            "display_name": {"editable": True, "risk": "medium"},
            "active_in_kiosk": {"editable": True, "risk": "high"},
            "technical": {"editable": True, "risk": "high", "requires_confirmation": True},
        },
    }


def _runtime_available(machine_key: str) -> Optional[bool]:
    runtime = machine_control._store.get_machine(machine_key)
    return runtime.available if runtime else None


def validate_machine_update(db, machine_name: str, payload: Mapping[str, Any]) -> Tuple[Optional[dict], Dict[str, str]]:
    if not isinstance(payload, Mapping):
        return None, {"payload": "Expected JSON object."}
    machine = _get_machine(db, machine_name)
    if not machine:
        return None, {"machine": "Machine not found."}
    errors: Dict[str, str] = {}
    changes: Dict[str, Any] = {"machine": machine, "layout": {}, "machine_fields": {}, "device_fields": {}, "config_fields": {}}

    if "display_name" in payload:
        text = str(payload.get("display_name") or "").strip()
        if not 1 <= len(text) <= 64:
            errors["display_name"] = "Display name must be 1-64 characters."
        else:
            changes["machine_fields"]["ui_name"] = text
    if "active_in_kiosk" in payload:
        parsed, ok = _parse_bool(payload.get("active_in_kiosk"))
        if not ok:
            errors["active_in_kiosk"] = "Expected boolean."
        else:
            changes["machine_fields"]["is_enabled"] = 1 if parsed else 0
    if "short_label" in payload:
        text = str(payload.get("short_label") or "").strip()
        if len(text) > 12:
            errors["short_label"] = "Short label must be 12 characters or fewer."
        else:
            changes["layout"]["short_label"] = text
    if "type" in payload:
        machine_type = str(payload.get("type") or "").strip()
        if machine_type not in {"washer", "dryer"}:
            errors["type"] = "Machine type must be washer or dryer."
        else:
            changes["layout"]["type"] = machine_type
    if "description" in payload:
        text = str(payload.get("description") or "").strip()
        if len(text) > 160:
            errors["description"] = "Description must be 160 characters or fewer."
        else:
            changes["layout"]["description"] = text
    if "display_order" in payload:
        parsed, ok = _parse_int(payload.get("display_order"))
        if not ok or parsed < 1 or parsed > 99:
            errors["display_order"] = "Display order must be an integer from 1 to 99."
        else:
            changes["layout"]["display_order"] = parsed

    technical = payload.get("technical")
    if technical is not None:
        if not isinstance(technical, Mapping):
            errors["technical"] = "Expected technical object."
        else:
            _validate_technical_update(db, machine, technical, errors, changes)
            if _has_technical_changes(changes) and not payload.get("confirm_high_risk"):
                errors["confirm_high_risk"] = "Confirm high-risk technical mapping changes before saving."

    return (changes if not errors else None), errors


# Machine fields whose change can start the wrong physical machine or break
# availability reporting; recorded as high risk in the audit trail.
_HIGH_RISK_MACHINE_FIELDS = {
    "uni_relay_channel",
    "i4_button_index",
    "is_enabled",
    "ip",
    "relay_channel",
    "metric_source",
    "on_threshold",
    "off_threshold",
    "on_confirm_ms",
    "off_confirm_ms",
    "poll_interval_ms",
}


def _audit_machine_field(db, machine_key: str, field: str, previous, value) -> None:
    if previous == value:
        return
    record_audit_entry(
        db,
        entity_type=ENTITY_MACHINE,
        entity_key=machine_key,
        field=field,
        old_value=previous,
        new_value=value,
        is_high_risk=field in _HIGH_RISK_MACHINE_FIELDS,
    )


def apply_machine_update(db, changes: Mapping[str, Any]) -> dict:
    """Apply one machine update and commit it."""

    try:
        _apply_machine_changes(db, changes)
        db.commit()
    except Exception:
        db.rollback()
        raise
    machine: Machine = changes["machine"]
    db.refresh(machine)
    return _machine_payload(machine, load_machine_card_layout(db), 1)


def _apply_machine_changes(db, changes: Mapping[str, Any]) -> None:
    """Stage one machine's changes. Never commits: it rides the caller's transaction."""

    machine: Machine = changes["machine"]
    machine_key = machine.name
    for field, value in changes["machine_fields"].items():
        _audit_machine_field(db, machine_key, field, getattr(machine, field, None), value)
        setattr(machine, field, value)
    if changes["device_fields"] and machine.uni_device:
        for field, value in changes["device_fields"].items():
            _audit_machine_field(
                db, machine_key, f"device.{field}", getattr(machine.uni_device, field, None), value
            )
            setattr(machine.uni_device, field, value)
        if hasattr(machine.uni_device, "updated_at"):
            machine.uni_device.updated_at = datetime.utcnow()
    if changes["config_fields"]:
        if not machine.config:
            machine.config = MachineConfig(machine_id=machine.id, on_threshold=8, off_threshold=3, on_confirm_ms=1200, off_confirm_ms=3000, poll_interval_ms=1000)
            db.add(machine.config)
        for field, value in changes["config_fields"].items():
            _audit_machine_field(
                db, machine_key, f"config.{field}", getattr(machine.config, field, None), value
            )
            setattr(machine.config, field, value)
    if "relay_channel" in changes["machine_fields"] and machine.uni_device:
        machine.uni_device.relay_channel = changes["machine_fields"]["relay_channel"]

    if changes["layout"]:
        layout = load_machine_card_layout(db)
        layout_entry = _mutable_layout_entry(layout, machine.name, machine.ui_name)
        for field, value in changes["layout"].items():
            _audit_machine_field(
                db, machine_key, f"layout.{field}", layout_entry.get(field), value
            )
        layout_entry.update(changes["layout"])
        _store_layout(db, layout)


def validate_machine_order(db, order: Any) -> Tuple[Optional[dict], Dict[str, str]]:
    if not isinstance(order, list):
        return None, {"order": "Expected an array of machine keys."}
    keys = [str(item).strip() for item in order]
    if any(not key for key in keys):
        return None, {"order": "Machine keys must be non-empty strings."}
    if len(set(keys)) != len(keys):
        return None, {"order": "Machine order contains duplicates."}
    existing = {machine.name for machine in db.query(Machine).all()}
    missing = [key for key in keys if key not in existing]
    if missing:
        return None, {"order": f"Unknown machine keys: {', '.join(missing)}."}
    return {"order": keys}, {}


def apply_machine_order(db, validated: Mapping[str, Any]) -> dict:
    """Apply a display-order change and commit it."""

    try:
        _apply_machine_order_entries(db, validated)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return build_machines_payload(db)


def _apply_machine_order_entries(db, validated: Mapping[str, Any]) -> None:
    """Stage the display order. Never commits: it rides the caller's transaction."""

    layout = load_machine_card_layout(db)
    machine_map = {machine.name: machine for machine in db.query(Machine).all()}
    for index, key in enumerate(validated["order"], start=1):
        machine = machine_map[key]
        entry = _mutable_layout_entry(layout, key, machine.ui_name)
        entry["display_order"] = index
    _store_layout(db, layout)


def validate_machine_updates(
    db, updates: Any
) -> Tuple[Optional[list], Dict[str, Dict[str, str]]]:
    """Validate a whole batch of machine payloads before anything is applied.

    Card edits are saved as one unit, so a single bad row must not leave the other
    machines already written.
    """

    if not isinstance(updates, list):
        return None, {"updates": {"updates": "Expected an array of machine updates."}}

    validated = []
    errors: Dict[str, Dict[str, str]] = {}
    seen_keys = set()
    for entry in updates:
        if not isinstance(entry, Mapping):
            errors["updates"] = {"updates": "Each update must be an object."}
            continue
        payload = dict(entry)
        machine_key = str(payload.pop("machine_key", "") or "").strip()
        if not machine_key:
            errors["updates"] = {"machine_key": "Every update needs a machine_key."}
            continue
        if machine_key in seen_keys:
            errors[machine_key] = {"machine_key": "Duplicate machine in this save."}
            continue
        seen_keys.add(machine_key)
        changes, machine_errors = validate_machine_update(db, machine_key, payload)
        if machine_errors:
            errors[machine_key] = machine_errors
        else:
            validated.append(changes)

    if not errors:
        errors.update(_batch_button_index_conflicts(db, validated))

    return (validated if not errors else None), errors


def _batch_button_index_conflicts(db, validated: list) -> Dict[str, Dict[str, str]]:
    """Catch I4 button collisions created *within* one batch.

    ``_button_index_conflicts`` only compares against committed rows, so two cards
    moved onto the same index in a single save would both pass on their own.
    """

    effective: Dict[str, Tuple[Any, bool]] = {}
    changed_keys = set()
    for changes in validated:
        machine = changes["machine"]
        fields = changes["machine_fields"]
        changed_keys.add(machine.name)
        effective[machine.name] = (
            fields.get("i4_button_index", machine.i4_button_index),
            bool(fields.get("is_enabled", machine.is_enabled)),
        )
    for machine in db.query(Machine).all():
        effective.setdefault(machine.name, (machine.i4_button_index, bool(machine.is_enabled)))

    errors: Dict[str, Dict[str, str]] = {}
    owner_by_index: Dict[Any, str] = {}
    for name in sorted(effective):
        index, enabled = effective[name]
        if index is None or not enabled:
            continue
        other = owner_by_index.get(index)
        if other is None:
            owner_by_index[index] = name
            continue
        for candidate, conflicting in ((name, other), (other, name)):
            if candidate in changed_keys:
                errors.setdefault(candidate, {})["technical.i4_button_index"] = (
                    f"I4 button index {index} is also used by {conflicting} in this save."
                )
    return errors


def apply_machine_updates(db, validated: list, order: Optional[list] = None) -> dict:
    """Apply a validated batch of machine updates and the layout order atomically."""

    try:
        for changes in validated:
            _apply_machine_changes(db, changes)
        if order:
            _apply_machine_order_entries(db, {"order": order})
        db.commit()
    except Exception:
        db.rollback()
        raise
    return build_machines_payload(db)


def build_export_config(db) -> dict:
    settings = {}
    secret_metadata = {}
    for setting in db.query(Settings).order_by(Settings.key.asc()).all():
        if setting.key in SECRET_KEYS:
            secret_metadata[f"{setting.key}_is_set"] = bool(setting.value)
        elif setting.key in SETTING_SCHEMA or setting.key == MACHINE_CARD_LAYOUT_KEY:
            settings[setting.key] = setting.value
    machines = []
    for machine in _query_machines(db):
        machines.append({
            "id": machine.id,
            "name": machine.name,
            "ui_name": machine.ui_name,
            "uni_device_id": machine.uni_device_id,
            "uni_relay_channel": machine.uni_relay_channel,
            "i4_device_id": machine.i4_device_id,
            "i4_button_index": machine.i4_button_index,
            "is_enabled": machine.is_enabled,
        })
    devices = [
        {
            "id": device.id,
            "name": device.name,
            "role": device.role,
            "model": device.model,
            "ip": device.ip,
            "relay_channel": device.relay_channel,
            "input_channel": device.input_channel,
            "metric_source": device.metric_source,
        }
        for device in db.query(Device).order_by(Device.id.asc()).all()
    ]
    configs = [
        {
            "machine_id": config.machine_id,
            "on_threshold": config.on_threshold,
            "off_threshold": config.off_threshold,
            "on_confirm_ms": config.on_confirm_ms,
            "off_confirm_ms": config.off_confirm_ms,
            "poll_interval_ms": config.poll_interval_ms,
        }
        for config in db.query(MachineConfig).order_by(MachineConfig.machine_id.asc()).all()
    ]
    return {
        "exported_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "settings": settings,
        "secret_metadata": secret_metadata,
        "machines": machines,
        "devices": devices,
        "machine_configs": configs,
        "machine_card_layout": load_machine_card_layout(db),
    }


def _validate_technical_update(db, machine: Machine, technical: Mapping[str, Any], errors: Dict[str, str], changes: Dict[str, Any]) -> None:
    # Ignore unsupported fields instead of erroring, as the frontend sends back read-only metadata fields.
    if "shelly_ip" in technical:
        value = str(technical.get("shelly_ip") or "").strip()
        if not _valid_host(value):
            errors["technical.shelly_ip"] = "Expected valid IPv4 address or hostname."
        else:
            changes["device_fields"]["ip"] = value
    if "relay_channel" in technical:
        parsed, ok = _parse_int(technical.get("relay_channel"))
        if not ok or parsed < 0 or parsed > 3:
            errors["technical.relay_channel"] = "Relay channel must be an integer from 0 to 3."
        else:
            changes["machine_fields"]["uni_relay_channel"] = parsed
            changes["device_fields"]["relay_channel"] = parsed
    if "i4_button_index" in technical:
        raw = technical.get("i4_button_index")
        if raw in (None, ""):
            parsed = None
            ok = True
        else:
            parsed, ok = _parse_int(raw)
        if not ok or (parsed is not None and (parsed < 0 or parsed > 15)):
            errors["technical.i4_button_index"] = "I4 button index must be 0-15 or blank."
        elif parsed is not None and _button_index_conflicts(db, machine.name, parsed):
            errors["technical.i4_button_index"] = "Another active machine already uses this I4 button index."
        else:
            changes["machine_fields"]["i4_button_index"] = parsed
    if "metric_source" in technical:
        source = str(technical.get("metric_source") or "").strip()
        if source not in METRIC_SOURCES:
            errors["technical.metric_source"] = f"Expected one of: {', '.join(sorted(METRIC_SOURCES))}."
        else:
            changes["device_fields"]["metric_source"] = source
    for field, minimum, maximum in (
        ("on_threshold", 0, 100000),
        ("off_threshold", 0, 100000),
        ("on_confirm_ms", 0, 60000),
        ("off_confirm_ms", 0, 60000),
        ("poll_interval_ms", 500, 60000),
    ):
        if field in technical:
            parsed, ok = _parse_int(technical.get(field))
            if not ok or parsed < minimum or parsed > maximum:
                errors[f"technical.{field}"] = f"{field} must be an integer from {minimum} to {maximum}."
            else:
                changes["config_fields"][field] = parsed


def _has_technical_changes(changes: Mapping[str, Any]) -> bool:
    if changes.get("device_fields") or changes.get("config_fields"):
        return True
    technical_machine_fields = {"uni_relay_channel", "i4_button_index"}
    return any(field in technical_machine_fields for field in changes.get("machine_fields", {}))


def _get_machine(db, machine_name: str) -> Optional[Machine]:
    return (
        db.query(Machine)
        .options(joinedload(Machine.uni_device), joinedload(Machine.i4_device), joinedload(Machine.config))
        .filter(Machine.name == machine_name)
        .first()
    )


def _mutable_layout_entry(layout: dict, machine_key: str, display_name: str) -> dict:
    machines = layout.setdefault("machines", {})
    if not isinstance(machines, dict):
        machines = {}
        layout["machines"] = machines
    entry = machines.get(machine_key)
    if not isinstance(entry, dict):
        entry = {}
        machines[machine_key] = entry
    entry.setdefault("display_order", len(machines))
    entry.setdefault("type", infer_machine_type(machine_key, display_name))
    entry.setdefault("short_label", default_short_label(machine_key, display_name))
    entry.setdefault("description", "")
    return entry


def _store_layout(db, layout: Mapping[str, Any]) -> None:
    stored = serialize_machine_card_layout(layout)
    setting = db.query(Settings).filter_by(key=MACHINE_CARD_LAYOUT_KEY).first()
    if setting:
        setting.value = stored
    else:
        db.add(Settings(key=MACHINE_CARD_LAYOUT_KEY, value=stored))


def _button_index_conflicts(db, machine_name: str, index: int) -> bool:
    return (
        db.query(Machine)
        .filter(Machine.name != machine_name)
        .filter(Machine.is_enabled == 1)
        .filter(Machine.i4_button_index == index)
        .first()
        is not None
    )


def _valid_host(value: str) -> bool:
    if not value:
        return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return bool(_HOST_RE.match(value)) and ".." not in value and len(value) <= 253


def _parse_bool(value: Any, default: Optional[bool] = None) -> Tuple[bool, bool]:
    if isinstance(value, bool):
        return value, True
    if value is None:
        return (bool(default), default is not None)
    text = str(value).strip().lower()
    if text in BOOL_TRUE:
        return True, True
    if text in BOOL_FALSE:
        return False, True
    return bool(default), False


def _parse_int(value: Any) -> Tuple[int, bool]:
    if isinstance(value, bool):
        return 0, False
    try:
        if isinstance(value, float) and not value.is_integer():
            return 0, False
        return int(value), True
    except (TypeError, ValueError):
        return 0, False


def _parse_float(value: Any) -> Tuple[float, bool]:
    if isinstance(value, bool):
        return 0.0, False
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0, False
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return 0.0, False
    return parsed, True


def _range_error(value: float, schema: Mapping[str, Any]) -> Optional[str]:
    if "min" in schema and value < schema["min"]:
        return f"Value must be at least {schema['min']}."
    if "max" in schema and value > schema["max"]:
        return f"Value must be at most {schema['max']}."
    return None


def _safe_int(value: Any, default: int) -> int:
    parsed, ok = _parse_int(value)
    return parsed if ok else default


def _safe_float(value: Any, default: float) -> float:
    parsed, ok = _parse_float(value)
    return parsed if ok else default
