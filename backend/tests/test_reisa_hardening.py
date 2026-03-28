import json

from backend.integrations.reisa_contract import (
    REISA_ACTION_COMPLETION_DEFAULT,
    decode_provider_reference,
    encode_provider_reference,
)
from backend.services.reisa_audit_service import _safe_json
from backend.setup.seed_settings import DEFAULT_SETTINGS


class _Entitlement:
    provider = "reisa"
    token = "uuid-token"
    external_id = "ext-1"
    booking_number = "booking-1"
    transaction_number = "txn-1"
    service_id = "svc-1"
    pin_code = "1234"
    code = "abc"


def test_reisa_provider_reference_roundtrip_json():
    encoded = encode_provider_reference(_Entitlement(), fallback_identifier="fallback")
    assert encoded is not None
    decoded = decode_provider_reference(encoded)
    assert decoded["token"] == "uuid-token"
    assert decoded["transaction_number"] == "txn-1"
    assert decoded["identifier"] == "abc"


def test_reisa_audit_safe_json_redacts_sensitive_values():
    payload = {
        "action": "WASHING_MACHINE_START",
        "token": "secret-token",
        "nested": {"pin_code": "9999", "ok": "yes"},
    }
    redacted = _safe_json(payload)
    assert redacted is not None
    parsed = json.loads(redacted)
    assert parsed["token"] == "[REDACTED]"
    assert parsed["nested"]["pin_code"] == "[REDACTED]"
    assert parsed["nested"]["ok"] == "yes"


def test_reisa_completion_default_action_matches_documented_contract():
    assert REISA_ACTION_COMPLETION_DEFAULT == "WASHING_MACHINE_COMPLETE"
    assert DEFAULT_SETTINGS["reisa_action_completion"] == "WASHING_MACHINE_COMPLETE"
