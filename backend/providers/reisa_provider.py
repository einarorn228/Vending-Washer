"""Reisa-backed provider."""

from __future__ import annotations

import logging
import time
from typing import Optional

from backend.integrations.reisa_client import ReisaClient, ReisaClientError
from backend.integrations.reisa_contract import (
    REISA_ACTION_COMPLETION_DEFAULT,
    REISA_ACTION_START_DEFAULT,
)
from backend.integrations.reisa_service import ReisaEntitlement, ReisaService, ReisaServiceError
from backend.providers.base_provider import (
    BaseProvider,
    ProviderAuthorizationResult,
    ProviderCommitResult,
    ProviderCompletionResult,
    ProviderLookupResult,
)
from backend.services.reisa_audit_service import (
    REQUEST_COMPLETION_STATUS,
    REQUEST_DEDUCT,
    REQUEST_LOOKUP,
    REQUEST_START_STATUS,
    RESULT_ERROR,
    RESULT_OK,
    record_reisa_audit,
)

logger = logging.getLogger(__name__)


class ReisaProvider(BaseProvider):
    """Provider implementation for Reisa entitlement and confirmed-start commit."""

    def __init__(
        self,
        *,
        base_url: str,
        bearer_token: str,
        connect_timeout_ms: int,
        read_timeout_ms: int,
        action_start: str = REISA_ACTION_START_DEFAULT,
        action_completion: str = REISA_ACTION_COMPLETION_DEFAULT,
    ) -> None:
        self.service = ReisaService(
            ReisaClient(
                base_url=base_url,
                bearer_token=bearer_token,
                connect_timeout_ms=connect_timeout_ms,
                read_timeout_ms=read_timeout_ms,
            )
        )
        self.action_start = (action_start or REISA_ACTION_START_DEFAULT).strip() or REISA_ACTION_START_DEFAULT
        self.action_completion = (action_completion or REISA_ACTION_COMPLETION_DEFAULT).strip() or REISA_ACTION_COMPLETION_DEFAULT

    def lookup(self, identifier: str, mode: str = "auto") -> ProviderLookupResult:
        value = (identifier or "").strip()
        if not value:
            return ProviderLookupResult(success=False, message="Missing code")

        request_path = f"/{'uuid' if mode == 'uuid' else ('pin' if mode == 'pin' else 'lookup')}/{value}"
        started = time.perf_counter()
        try:
            if mode == "uuid":
                entitlement = self.service.lookup_by_uuid(value)
            elif mode == "pin":
                entitlement = self.service.lookup_by_pin(value)
            else:
                entitlement = self.service.lookup_auto(value)
            record_reisa_audit(
                request_type=REQUEST_LOOKUP,
                endpoint=request_path,
                method="GET",
                result=RESULT_OK,
                provider_reference=getattr(entitlement, "token", None) or getattr(entitlement, "external_id", None),
                response_payload={
                    "lookup_mode": mode,
                    "uses_left": getattr(entitlement, "uses_left", None),
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            return ProviderLookupResult(success=True, message="", entitlement=entitlement)
        except ReisaServiceError as exc:
            record_reisa_audit(
                request_type=REQUEST_LOOKUP,
                endpoint=request_path,
                method="GET",
                result=RESULT_ERROR,
                request_payload={"lookup_mode": mode},
                retryable=exc.retryable,
                error_message=exc.message,
                response_payload={"latency_ms": int((time.perf_counter() - started) * 1000)},
            )
            return ProviderLookupResult(success=False, message=exc.message, entitlement=None)
        except ReisaClientError as exc:
            record_reisa_audit(
                request_type=REQUEST_LOOKUP,
                endpoint=request_path,
                method="GET",
                result=RESULT_ERROR,
                request_payload={"lookup_mode": mode},
                response_status_code=exc.status_code,
                retryable=exc.retryable,
                error_message=exc.message,
                response_payload={"latency_ms": int((time.perf_counter() - started) * 1000)},
            )
            return ProviderLookupResult(success=False, message=exc.message, entitlement=None)

    def authorize(self, entitlement, machine_id: Optional[str] = None) -> ProviderAuthorizationResult:
        if not isinstance(entitlement, ReisaEntitlement):
            return ProviderAuthorizationResult(authorized=False, message="Invalid Reisa entitlement", entitlement=None)

        if entitlement.uses_left <= 0:
            return ProviderAuthorizationResult(authorized=False, message="No remaining uses", entitlement=None)

        return ProviderAuthorizationResult(authorized=True, message="", entitlement=entitlement)

    def commit_start(self, entitlement, quantity: int = 1) -> ProviderCommitResult:
        if not isinstance(entitlement, ReisaEntitlement):
            return ProviderCommitResult(success=False, message="Invalid Reisa entitlement", uses_left=None, retryable=False)

        uuid = (entitlement.token or "").strip()
        if not uuid:
            return ProviderCommitResult(
                success=False,
                message="Missing Reisa UUID/token for commit",
                uses_left=None,
                retryable=False,
            )

        qty = max(int(quantity), 1)
        session_uid = (getattr(entitlement, "session_uid", None) or "").strip() or None
        provider_reference = entitlement.token or entitlement.external_id

        try:
            self.service.post_start_status(uuid, action=self.action_start)
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_START_STATUS,
                endpoint=f"/uuid/{uuid}/status",
                method="POST",
                result=RESULT_OK,
                provider_reference=provider_reference,
                request_payload={"action": self.action_start},
            )
        except ReisaServiceError as exc:
            logger.warning(
                "Reisa start status failed",
                extra={"external_id": entitlement.external_id, "retryable": exc.retryable},
            )
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_START_STATUS,
                endpoint=f"/uuid/{uuid}/status",
                method="POST",
                result=RESULT_ERROR,
                provider_reference=provider_reference,
                request_payload={"action": self.action_start},
                retryable=exc.retryable,
                error_message=exc.message,
            )
            return ProviderCommitResult(success=False, message=exc.message, uses_left=None, retryable=exc.retryable)
        except ReisaClientError as exc:
            logger.warning(
                "Reisa start status client failure",
                extra={"external_id": entitlement.external_id, "retryable": exc.retryable},
            )
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_START_STATUS,
                endpoint=f"/uuid/{uuid}/status",
                method="POST",
                result=RESULT_ERROR,
                provider_reference=provider_reference,
                request_payload={"action": self.action_start},
                response_status_code=exc.status_code,
                retryable=exc.retryable,
                error_message=exc.message,
            )
            return ProviderCommitResult(success=False, message=exc.message, uses_left=None, retryable=exc.retryable)

        try:
            deduct = self.service.deduct_usage(uuid, quantity=qty)
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_DEDUCT,
                endpoint=f"/uuid/{uuid}/deduct",
                method="POST",
                result=RESULT_OK,
                provider_reference=provider_reference,
                request_payload={"quantity": qty},
                response_payload=deduct.raw,
            )
            uses_left = deduct.uses_left if deduct.uses_left is not None else max(entitlement.uses_left - qty, 0)
            return ProviderCommitResult(success=True, message="", uses_left=uses_left, retryable=False)
        except ReisaServiceError as exc:
            logger.warning(
                "Reisa deduct failed",
                extra={"external_id": entitlement.external_id, "retryable": exc.retryable},
            )
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_DEDUCT,
                endpoint=f"/uuid/{uuid}/deduct",
                method="POST",
                result=RESULT_ERROR,
                provider_reference=provider_reference,
                request_payload={"quantity": qty},
                retryable=exc.retryable,
                error_message=exc.message,
            )
            return ProviderCommitResult(success=False, message=exc.message, uses_left=None, retryable=exc.retryable)
        except ReisaClientError as exc:
            logger.warning(
                "Reisa deduct client failure",
                extra={"external_id": entitlement.external_id, "retryable": exc.retryable},
            )
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_DEDUCT,
                endpoint=f"/uuid/{uuid}/deduct",
                method="POST",
                result=RESULT_ERROR,
                provider_reference=provider_reference,
                request_payload={"quantity": qty},
                response_status_code=exc.status_code,
                retryable=exc.retryable,
                error_message=exc.message,
            )
            return ProviderCommitResult(success=False, message=exc.message, uses_left=None, retryable=exc.retryable)

    def mark_completion(self, entitlement, machine_id: Optional[str] = None) -> ProviderCompletionResult:
        if entitlement is None:
            return ProviderCompletionResult(success=False, message="Invalid Reisa entitlement")

        uuid = (getattr(entitlement, "token", None) or "").strip()
        if not uuid:
            return ProviderCompletionResult(
                success=False,
                message="Missing Reisa UUID/token for completion",
            )

        session_uid = (getattr(entitlement, "session_uid", None) or "").strip() or None
        provider_reference = getattr(entitlement, "token", None) or getattr(entitlement, "external_id", None)

        try:
            self.service.post_completion_status(uuid, action=self.action_completion)
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_COMPLETION_STATUS,
                endpoint=f"/uuid/{uuid}/status",
                method="POST",
                result=RESULT_OK,
                provider_reference=provider_reference,
                request_payload={"action": self.action_completion, "machine_id": machine_id},
            )
            return ProviderCompletionResult(success=True, message="")
        except ReisaServiceError as exc:
            logger.warning(
                "Reisa completion status failed",
                extra={
                    "machine_id": machine_id,
                    "external_id": getattr(entitlement, "external_id", None),
                    "retryable": exc.retryable,
                },
            )
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_COMPLETION_STATUS,
                endpoint=f"/uuid/{uuid}/status",
                method="POST",
                result=RESULT_ERROR,
                provider_reference=provider_reference,
                request_payload={"action": self.action_completion, "machine_id": machine_id},
                retryable=exc.retryable,
                error_message=exc.message,
            )
            return ProviderCompletionResult(success=False, message=exc.message)
        except ReisaClientError as exc:
            logger.warning(
                "Reisa completion status client failure",
                extra={
                    "machine_id": machine_id,
                    "external_id": getattr(entitlement, "external_id", None),
                    "retryable": exc.retryable,
                },
            )
            record_reisa_audit(
                session_uid=session_uid,
                request_type=REQUEST_COMPLETION_STATUS,
                endpoint=f"/uuid/{uuid}/status",
                method="POST",
                result=RESULT_ERROR,
                provider_reference=provider_reference,
                request_payload={"action": self.action_completion, "machine_id": machine_id},
                response_status_code=exc.status_code,
                retryable=exc.retryable,
                error_message=exc.message,
            )
            return ProviderCompletionResult(success=False, message=exc.message)
