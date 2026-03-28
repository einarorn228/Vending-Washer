import json
from uuid import uuid4

from backend.integrations.reisa_contract import (
    REISA_ACTION_COMPLETION_DEFAULT,
    decode_provider_reference,
    encode_provider_reference,
)
from backend.integrations.reisa_service import ReisaCommitStartResult
from backend.models import init_db
from backend.providers.reisa_provider import ReisaProvider
from backend.services.reisa_audit_service import (
    REQUEST_DEDUCT,
    REQUEST_START_STATUS,
    RESULT_ERROR,
    RESULT_OK,
    _safe_json,
    list_audit_events_for_session,
    record_reisa_audit,
)
from backend.services.reisa_diagnostics_service import get_reisa_session_diagnostics
from backend.services.reisa_replay_service import replay_retry_job
from backend.services.reisa_retry_service import create_retry_job, list_retry_jobs
from backend.services.usage_session_service import create_usage_session, get_usage_session
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


class _FakeReisaService:
    def __init__(self):
        self.start_calls = 0
        self.deduct_calls = 0
        self.completion_calls = 0

    def post_start_status(self, uuid: str, *, action: str):
        self.start_calls += 1
        return {"ok": True, "uuid": uuid, "action": action}

    def deduct_usage(self, uuid: str, *, quantity: int = 1):
        self.deduct_calls += 1
        return ReisaCommitStartResult(uses_left=3, raw={"remainingQuantity": 3, "uuid": uuid, "quantity": quantity})

    def post_completion_status(self, uuid: str, *, action: str):
        self.completion_calls += 1
        return {"ok": True, "uuid": uuid, "action": action}


def _fake_provider() -> ReisaProvider:
    provider = ReisaProvider(
        base_url="http://example.invalid",
        bearer_token="test-token",
        connect_timeout_ms=100,
        read_timeout_ms=100,
    )
    provider.service = _FakeReisaService()
    return provider


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


def test_retry_job_created_for_retryable_reisa_sync_failure():
    init_db()
    session_uid = f"test-retry-{uuid4().hex}"

    record_reisa_audit(
        session_uid=session_uid,
        request_type=REQUEST_START_STATUS,
        endpoint="/uuid/uuid-token/status",
        method="POST",
        result=RESULT_ERROR,
        retryable=True,
        error_message="timeout",
        request_payload={"action": "WASHING_MACHINE_START"},
    )

    jobs = [
        row
        for row in list_retry_jobs(limit=500)
        if row["session_uid"] == session_uid and row["action_type"] == "start_status"
    ]
    assert jobs
    assert jobs[0]["correlation"]["source_audit_log_id"] is not None
    assert jobs[0]["failure_category"] in {"network_timeout", "unexpected_response"}


def test_replay_skips_when_start_status_already_synced():
    init_db()
    session_uid = create_usage_session(
        provider="reisa",
        provider_reference='{"token":"uuid-token"}',
        identifier_type="uuid_or_pin",
        identifier_value="1234",
        machine_id="washer-2",
        scan_source="api",
        state="start_confirmed",
        requested_quantity=1,
    )

    record_reisa_audit(
        session_uid=session_uid,
        request_type=REQUEST_START_STATUS,
        endpoint="/uuid/uuid-token/status",
        method="POST",
        result=RESULT_OK,
        retryable=False,
        request_payload={"action": "WASHING_MACHINE_START"},
    )

    job_id = create_retry_job(
        session_uid=session_uid,
        action_type="start_status",
        provider_reference="uuid-token",
        request_payload_redacted='{"action":"WASHING_MACHINE_START"}',
        last_error="timeout",
    )
    assert job_id is not None

    outcome = replay_retry_job(job_id)
    assert outcome.success is True
    assert outcome.status == "skipped"


def test_replay_deduct_repairs_local_commit_state(monkeypatch):
    init_db()
    session_uid = create_usage_session(
        provider="reisa",
        provider_reference='{"token":"uuid-token"}',
        identifier_type="uuid_or_pin",
        identifier_value="1234",
        machine_id="washer-3",
        scan_source="api",
        state="failed",
        requested_quantity=1,
    )

    from backend.services import usage_session_service as us
    us.mark_external_sync_failed(session_uid, error_code="commit_failed", error_detail="timeout")

    job_id = create_retry_job(session_uid=session_uid, action_type="deduct", provider_reference="uuid-token")
    assert job_id is not None

    provider = _fake_provider()
    monkeypatch.setattr("backend.services.reisa_replay_service.resolve_provider_by_name", lambda _name: provider)

    outcome = replay_retry_job(job_id)
    assert outcome.success is True

    repaired = get_usage_session(session_uid)
    assert repaired is not None
    assert repaired.state == "commit_ok"
    assert repaired.committed_quantity == 1
    assert repaired.remaining_after_commit == 3
    assert repaired.error_code is None


def test_replay_completion_clears_completion_sync_failure(monkeypatch):
    init_db()
    session_uid = create_usage_session(
        provider="reisa",
        provider_reference='{"token":"uuid-token"}',
        identifier_type="uuid_or_pin",
        identifier_value="1234",
        machine_id="washer-4",
        scan_source="api",
        state="completed",
        requested_quantity=1,
    )

    from backend.services import usage_session_service as us
    us.mark_external_sync_failed(session_uid, error_code="completion_sync_failed", error_detail="timeout")

    job_id = create_retry_job(session_uid=session_uid, action_type="completion_status", provider_reference="uuid-token")
    assert job_id is not None

    provider = _fake_provider()
    monkeypatch.setattr("backend.services.reisa_replay_service.resolve_provider_by_name", lambda _name: provider)

    outcome = replay_retry_job(job_id)
    assert outcome.success is True

    repaired = get_usage_session(session_uid)
    assert repaired is not None
    assert repaired.state == "completed"
    assert repaired.error_code is None


def test_replay_start_status_also_attempts_deduct_and_repairs_commit(monkeypatch):
    init_db()
    session_uid = create_usage_session(
        provider="reisa",
        provider_reference='{"token":"uuid-token"}',
        identifier_type="uuid_or_pin",
        identifier_value="1234",
        machine_id="washer-5",
        scan_source="api",
        state="start_confirmed",
        requested_quantity=1,
    )

    job_id = create_retry_job(session_uid=session_uid, action_type="start_status", provider_reference="uuid-token")
    assert job_id is not None

    provider = _fake_provider()
    monkeypatch.setattr("backend.services.reisa_replay_service.resolve_provider_by_name", lambda _name: provider)

    outcome = replay_retry_job(job_id)
    assert outcome.success is True

    service = provider.service
    assert service.start_calls == 1
    assert service.deduct_calls == 1

    repaired = get_usage_session(session_uid)
    assert repaired is not None
    assert repaired.state == "commit_ok"
    assert repaired.error_code is None

    deduct_events = list_audit_events_for_session(session_uid=session_uid, request_type=REQUEST_DEDUCT, result=RESULT_OK)
    assert deduct_events


def test_session_diagnostics_returns_correlated_operator_snapshot(monkeypatch):
    init_db()
    session_uid = create_usage_session(
        provider="reisa",
        provider_reference='{"token":"uuid-token"}',
        identifier_type="uuid_or_pin",
        identifier_value="1234",
        machine_id="washer-6",
        scan_source="api",
        state="start_confirmed",
        requested_quantity=1,
    )
    record_reisa_audit(
        session_uid=session_uid,
        request_type=REQUEST_START_STATUS,
        endpoint="/uuid/uuid-token/status",
        method="POST",
        result=RESULT_ERROR,
        retryable=True,
        error_message="timeout",
    )
    provider = _fake_provider()
    monkeypatch.setattr("backend.services.reisa_replay_service.resolve_provider_by_name", lambda _name: provider)
    jobs = [row for row in list_retry_jobs(limit=500) if row["session_uid"] == session_uid]
    assert jobs
    replay_retry_job(jobs[0]["id"])

    diagnostic = get_reisa_session_diagnostics(session_uid=session_uid, limit=50)
    assert diagnostic["session"]["session_uid"] == session_uid
    assert diagnostic["audit_events"]
    assert diagnostic["retry_jobs"]
    assert diagnostic["likely_next_operator_action"] in {
        "wait_or_run_retry_due",
        "review_latest_audit_and_replay",
        "create_or_review_retry_job",
        "investigate_session_context",
    }
