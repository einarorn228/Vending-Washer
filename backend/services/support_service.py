# backend/services/support_service.py
"""Allowlisted, read-only runtime projection for escalation reports.

One mechanism serves the support report today and system-aware guide cards and AI
context later. Guides name diagnostic groups; this module decides what a group means
and which fields are safe. The client never names a group or a field.
"""

import logging
from datetime import datetime

from backend.help.schema import CHECK_RESULTS
from backend.models.setting_model import get_setting_value, parse_setting_bool
from backend.services.dev_admin_service import SECRET_KEYS, scanner_status
from backend.services.help_service import get_guide, get_provenance

logger = logging.getLogger(__name__)

CORE_GROUPS = ("core", "kiosk.state", "settings.provider", "scanner.status")

SAFE_SETTING_KEYS = (
    "telemetry_enabled", "backend_relay_enabled", "button_box_enabled",
    "kiosk_input_mode", "provider_default", "provider_reisa_enabled",
    "machine_reservation_minutes", "relay_pulse_duration_sec",
    "shelly_http_timeout_sec", "telemetry_http_timeout_sec",
    "scan_timeout", "serial_port", "serial_baudrate",
)
assert not (set(SAFE_SETTING_KEYS) & SECRET_KEYS), "secret key leaked into the safe allowlist"

# Field names taken verbatim from MachineStateStore.get_diagnostic_snapshot().
_MACHINE_SECTIONS = {
    "machine.identity": ("identity", ("name", "is_enabled", "available", "run_state", "pending_start")),
    "machine.telemetry": ("telemetry", ("last_value", "band", "seconds_since_read",
                                        "seconds_above", "seconds_below")),
    "machine.thresholds": ("thresholds", ("config",)),
    "machine.mapping": ("mapping", ("device",)),
}


def _snapshot(machine_id):
    """Rows for the report's machine scope.

    Only ``None`` means "all machines". Any other value must be a non-empty string
    matching a machine id; a falsy or non-string value (``""``, ``{}``, ``0`` from a
    malformed request body) narrows to NOTHING rather than accidentally widening to
    every machine.
    """
    from backend.controllers.telemetry import MachineStateStore
    rows = MachineStateStore.instance().get_diagnostic_snapshot()
    if machine_id is None:
        return rows
    if not isinstance(machine_id, str) or not machine_id.strip():
        return []
    return [r for r in rows if r.get("id") == machine_id.strip()]


def _machine_group(group):
    subsection, fields = _MACHINE_SECTIONS[group]

    def handler(db, machine_id, data):
        machines = data.setdefault("machines", {})
        for row in _snapshot(machine_id):
            entry = machines.setdefault(row["id"], {})
            entry[subsection] = {f: row.get(f) for f in fields if f in row}

    return handler


def _core(db, machine_id, data):
    data.setdefault("app", {})["name"] = "Vending-Washer"


def _kiosk(db, machine_id, data):
    from backend.controllers.machine_control import UI_STATE
    data.setdefault("kiosk", {}).update({
        "state": UI_STATE.get("state"),
        "current_machine": UI_STATE.get("current_machine"),
    })


def _provider(db, machine_id, data):
    data.setdefault("provider", {}).update({
        "provider_default": get_setting_value(db, "provider_default"),
        "reisa_enabled": parse_setting_bool(
            get_setting_value(db, "provider_reisa_enabled"), default=False),
        "reisa_base_url_configured": bool(get_setting_value(db, "reisa_base_url")),
        "reisa_token_configured": bool(get_setting_value(db, "reisa_bearer_token")),
    })


def _scanner(db, machine_id, data):
    data.setdefault("scanner", {}).update(scanner_status(db))


def _settings_group(keys):
    unsafe = set(keys) - set(SAFE_SETTING_KEYS)
    if unsafe:
        raise ValueError(f"settings group names non-allowlisted keys: {sorted(unsafe)}")

    def handler(db, machine_id, data):
        section = data.setdefault("settings", {})
        for key in keys:
            if key in SAFE_SETTING_KEYS:   # belt and braces at read time too
                section[key] = get_setting_value(db, key)
    return handler


GROUP_HANDLERS = {
    "core": _core,
    "kiosk.state": _kiosk,
    "settings.provider": _provider,
    "provider.reisa": _provider,
    "scanner.status": _scanner,
    "machine.identity": _machine_group("machine.identity"),
    "machine.telemetry": _machine_group("machine.telemetry"),
    "machine.thresholds": _machine_group("machine.thresholds"),
    "machine.mapping": _machine_group("machine.mapping"),
    "settings.telemetry": _settings_group(("telemetry_enabled", "telemetry_http_timeout_sec")),
    "settings.relay": _settings_group(("backend_relay_enabled", "relay_pulse_duration_sec",
                                       "shelly_http_timeout_sec")),
    "settings.scanner": _settings_group(("scan_timeout", "serial_port", "serial_baudrate")),
}


def _resolve_groups(guide_id, groups):
    """Groups come from the guide, or from a caller inside this process.

    `groups` is not reachable from the HTTP layer: the route passes only `guide_id`.
    It exists so tests and future in-process consumers can request a projection
    directly without inventing a fake guide.
    """
    guide = get_guide(guide_id) if isinstance(guide_id, str) and guide_id.strip() else None
    resolved = list(CORE_GROUPS)
    declared = list(groups) if groups else (guide.get("diagnostics", []) if guide else [])
    for group in declared:
        if group in GROUP_HANDLERS and group not in resolved:
            resolved.append(group)
    return guide, resolved


def _clean_checks(checks):
    cleaned = []
    for check in checks or []:
        if not isinstance(check, dict):
            continue
        check_id, result = check.get("check_id"), check.get("result")
        if result in CHECK_RESULTS and isinstance(check_id, str) and check_id:
            cleaned.append({"check_id": check_id, "result": result})
    return cleaned


def build_support_report(db, guide_id=None, machine_id=None, checks=None,
                         locale="is", locale_shown=None, groups=None):
    guide, resolved = _resolve_groups(guide_id, groups)
    data = {}
    for group in resolved:
        try:
            GROUP_HANDLERS[group](db, machine_id, data)
        except Exception:  # one broken group must not sink the whole report
            # A fixed marker only: never the exception text, which could carry
            # internal paths or values the allowlist exists to keep out.
            data.setdefault("errors", {})[group] = "unavailable"
            logger.warning("support report: diagnostic group %s unavailable", group)

    return {
        "schema_version": 1,
        "generated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "help": get_provenance(),
        "guide_id": guide.get("id") if guide else None,
        "locale_requested": locale,
        "locale_shown": locale_shown or locale,
        "groups": resolved,
        "machine_id": machine_id,
        "checks": _clean_checks(checks),
        "data": data,
    }


_LABELS = {
    "is": {"title": "Stuðningsskýrsla", "checks": "Athuganir", "machines": "Vélar",
           "errors": "Villur við söfnun"},
    "en": {"title": "Support report", "checks": "Checks", "machines": "Machines",
           "errors": "Collection errors"},
}

# Human-readable order is by diagnostic importance, so a developer can read the top
# of a pasted report and understand the incident before scrolling. The structured
# JSON stays deterministic on its own; this order applies only to the rendered text.
SECTION_ORDER = ("app", "kiosk", "machines", "provider", "scanner", "settings", "errors")
MACHINE_SUBSECTION_ORDER = ("identity", "telemetry", "thresholds", "mapping")


def _ordered(keys, order):
    """Known keys in importance order, then anything unexpected alphabetically."""
    known = [k for k in order if k in keys]
    return known + sorted(k for k in keys if k not in order)


def render_report_text(report, locale="is"):
    labels = _LABELS.get(locale, _LABELS["en"])
    help_meta = report.get("help", {})
    data = report.get("data", {})
    lines = [
        f"# {labels['title']} — Vending-Washer",
        f"generated_at: {report['generated_at']}",
        f"guide_id: {report['guide_id']}",
        f"locale_requested: {report['locale_requested']}  locale_shown: {report['locale_shown']}",
        f"help_schema_version: {help_meta.get('schema_version')}",
        f"help_manifest_digest: {help_meta.get('manifest_digest')}",
        f"help_build_id: {help_meta.get('build_id')}",
    ]

    for section in _ordered(data.keys(), SECTION_ORDER):
        lines.append("")
        if section == "machines":
            lines.append(f"## {labels['machines']}")
            machines = data["machines"] or {}
            for machine_id in sorted(machines):
                lines.append(f"### {machine_id}")
                for sub in _ordered(machines[machine_id].keys(), MACHINE_SUBSECTION_ORDER):
                    for key, value in machines[machine_id][sub].items():
                        lines.append(f"- {sub}.{key}: {value}")
            continue
        title = labels["errors"] if section == "errors" else section
        lines.append(f"## {title}")
        for key, value in data[section].items():
            lines.append(f"- {key}: {value}")

    if report.get("checks"):
        lines.append("")
        lines.append(f"## {labels['checks']}")
        for check in report["checks"]:
            lines.append(f"- {check['check_id']}: {check['result']}")
    return "\n".join(lines)
