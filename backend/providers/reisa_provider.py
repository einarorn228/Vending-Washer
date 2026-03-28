"""Reisa-backed provider (Phase 5: read-only lookup/authorize)."""

from __future__ import annotations

import logging
from typing import Optional

from backend.integrations.reisa_client import ReisaClient, ReisaClientError
from backend.integrations.reisa_service import ReisaEntitlement, ReisaService, ReisaServiceError
from backend.providers.base_provider import (
    BaseProvider,
    ProviderAuthorizationResult,
    ProviderCommitResult,
    ProviderCompletionResult,
    ProviderLookupResult,
)

logger = logging.getLogger(__name__)


class ReisaProvider(BaseProvider):
    """Provider implementation for Reisa lookup + authorization only."""

    def __init__(self, *, base_url: str, bearer_token: str, connect_timeout_ms: int, read_timeout_ms: int) -> None:
        self.service = ReisaService(
            ReisaClient(
                base_url=base_url,
                bearer_token=bearer_token,
                connect_timeout_ms=connect_timeout_ms,
                read_timeout_ms=read_timeout_ms,
            )
        )

    def lookup(self, identifier: str, mode: str = "auto") -> ProviderLookupResult:
        value = (identifier or "").strip()
        if not value:
            return ProviderLookupResult(success=False, message="Missing code")

        try:
            if mode == "uuid":
                entitlement = self.service.lookup_by_uuid(value)
            elif mode == "pin":
                entitlement = self.service.lookup_by_pin(value)
            else:
                entitlement = self.service.lookup_auto(value)
            return ProviderLookupResult(success=True, message="", entitlement=entitlement)
        except ReisaServiceError as exc:
            return ProviderLookupResult(success=False, message=exc.message, entitlement=None)
        except ReisaClientError as exc:
            return ProviderLookupResult(success=False, message=exc.message, entitlement=None)

    def authorize(self, entitlement, machine_id: Optional[str] = None) -> ProviderAuthorizationResult:
        if not isinstance(entitlement, ReisaEntitlement):
            return ProviderAuthorizationResult(authorized=False, message="Invalid Reisa entitlement", entitlement=None)

        if entitlement.uses_left <= 0:
            return ProviderAuthorizationResult(authorized=False, message="No remaining uses", entitlement=None)

        return ProviderAuthorizationResult(authorized=True, message="", entitlement=entitlement)

    def commit_start(self, entitlement, quantity: int = 1) -> ProviderCommitResult:
        # Phase 5 is read-only. Do not call Reisa write endpoints yet.
        if isinstance(entitlement, ReisaEntitlement):
            return ProviderCommitResult(
                success=True,
                message="Reisa commit deferred (read-only mode)",
                uses_left=max(entitlement.uses_left, 0),
                retryable=False,
            )
        return ProviderCommitResult(success=False, message="Invalid Reisa entitlement", uses_left=None, retryable=False)

    def mark_completion(self, entitlement, machine_id: Optional[str] = None) -> ProviderCompletionResult:
        # Phase 5 is read-only. Completion/status posting intentionally not implemented.
        return ProviderCompletionResult(success=True, message="Reisa completion deferred (read-only mode)")
