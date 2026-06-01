"""Helpers for kiosk machine-card presentation metadata."""

from __future__ import annotations

import json
from typing import Dict, Iterable, Mapping, MutableMapping, Optional

from backend.models.setting_model import get_setting_value

MACHINE_CARD_LAYOUT_KEY = "machine_card_layout"
_LAYOUT_VERSION = 1


def infer_machine_type(machine_key: str, display_name: Optional[str] = None) -> str:
    text = f"{machine_key or ''} {display_name or ''}".lower()
    if "dryer" in text or text.startswith("dr") or "þurr" in text:
        return "dryer"
    return "washer"


def default_short_label(machine_key: str, display_name: Optional[str] = None) -> str:
    source = (display_name or machine_key or "").strip()
    if not source:
        return ""
    parts = [part for part in source.replace("-", " ").replace("_", " ").split() if part]
    if len(parts) >= 2:
        return "".join(part[0].upper() for part in parts[:2])[:6]
    return source[:6]


def _empty_layout() -> dict:
    return {"version": _LAYOUT_VERSION, "machines": {}}


def parse_machine_card_layout(raw: Optional[str]) -> dict:
    if not raw:
        return _empty_layout()
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return _empty_layout()
    if not isinstance(parsed, dict):
        return _empty_layout()
    machines = parsed.get("machines")
    if not isinstance(machines, dict):
        machines = {}
    return {"version": parsed.get("version") or _LAYOUT_VERSION, "machines": machines}


def serialize_machine_card_layout(layout: Mapping[str, object]) -> str:
    machines = layout.get("machines") if isinstance(layout, Mapping) else {}
    if not isinstance(machines, Mapping):
        machines = {}
    normalized = {"version": _LAYOUT_VERSION, "machines": machines}
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def load_machine_card_layout(db) -> dict:
    return parse_machine_card_layout(get_setting_value(db, MACHINE_CARD_LAYOUT_KEY, default=""))


def ensure_layout_entry(
    layout: MutableMapping[str, object],
    machine_key: str,
    *,
    display_name: Optional[str] = None,
    fallback_order: int = 999,
) -> dict:
    machines = layout.setdefault("machines", {})
    if not isinstance(machines, dict):
        machines = {}
        layout["machines"] = machines
    entry = machines.get(machine_key)
    if not isinstance(entry, dict):
        entry = {}
        machines[machine_key] = entry
    entry.setdefault("display_order", fallback_order)
    entry.setdefault("type", infer_machine_type(machine_key, display_name))
    entry.setdefault("short_label", default_short_label(machine_key, display_name))
    entry.setdefault("description", "")
    return entry


def machine_layout_entry(layout: Mapping[str, object], machine_key: str, display_name: Optional[str] = None, fallback_order: int = 999) -> dict:
    machines = layout.get("machines") if isinstance(layout, Mapping) else {}
    raw_entry = machines.get(machine_key) if isinstance(machines, Mapping) else None
    entry = raw_entry if isinstance(raw_entry, dict) else {}
    return {
        "display_order": _safe_int(entry.get("display_order"), fallback_order),
        "type": entry.get("type") if entry.get("type") in {"washer", "dryer"} else infer_machine_type(machine_key, display_name),
        "short_label": str(entry.get("short_label") or default_short_label(machine_key, display_name)),
        "description": str(entry.get("description") or ""),
    }


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def decorate_machine_snapshot(snapshot: Iterable[Mapping[str, object]], db) -> list:
    layout = load_machine_card_layout(db)
    decorated = []
    for index, machine in enumerate(snapshot, start=1):
        machine_id = str(machine.get("id") or "")
        display_name = str(machine.get("name") or machine_id)
        entry = machine_layout_entry(layout, machine_id, display_name, index)
        item = dict(machine)
        item["type"] = entry["type"]
        item["short_label"] = entry["short_label"]
        item["description"] = entry["description"]
        item["display_order"] = entry["display_order"]
        decorated.append(item)
    decorated.sort(key=lambda item: (item.get("display_order", 999), str(item.get("name") or ""), str(item.get("id") or "")))
    return decorated
