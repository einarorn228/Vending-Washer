"""Centralized Reisa contract constants and reference helpers."""

from __future__ import annotations

import json
from typing import Any, Optional

REISA_ACTION_START_DEFAULT = "WASHING_MACHINE_START"
REISA_ACTION_COMPLETION_DEFAULT = "WASHING_MACHINE_COMPLETE"


def encode_provider_reference(entitlement: Any, *, fallback_identifier: Optional[str] = None) -> Optional[str]:
    """Persist stable Reisa reference details in a single durable string field."""

    payload = {
        "token": getattr(entitlement, "token", None),
        "external_id": getattr(entitlement, "external_id", None),
        "booking_number": getattr(entitlement, "booking_number", None),
        "transaction_number": getattr(entitlement, "transaction_number", None),
        "service_id": getattr(entitlement, "service_id", None),
        "pin_code": getattr(entitlement, "pin_code", None),
        "identifier": getattr(entitlement, "code", None) or fallback_identifier,
    }
    compact = {k: v for k, v in payload.items() if v is not None and str(v).strip()}
    if not compact:
        return None
    return json.dumps(compact, ensure_ascii=False, sort_keys=True)


def decode_provider_reference(value: Optional[str]) -> dict[str, str]:
    raw = (value or "").strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, dict):
                return {str(k): str(v) for k, v in decoded.items() if v is not None and str(v).strip()}
        except Exception:
            return {}
    # Legacy rows stored only token/string directly.
    return {"token": raw, "external_id": raw, "identifier": raw}


def get_commit_uuid_from_reference(reference: Optional[str]) -> Optional[str]:
    decoded = decode_provider_reference(reference)
    for key in ("token", "external_id", "identifier"):
        value = (decoded.get(key) or "").strip()
        if value:
            return value
    return None
