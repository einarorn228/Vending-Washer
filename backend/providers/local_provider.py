"""Local DB-backed entitlement provider."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from backend.models import Session
from backend.models.code_model import Code
from backend.providers.base_provider import (
    BaseProvider,
    ProviderAuthorizationResult,
    ProviderCommitResult,
    ProviderCompletionResult,
    ProviderLookupResult,
)

logger = logging.getLogger(__name__)

INVALID_CODE_MESSAGE = "Code expired or invalid."


class LocalProvider(BaseProvider):
    """Provider implementation that preserves existing local code behavior."""

    def _get_session(self):
        return Session()

    def _to_validated_code(self, obj: Code):
        # Local import avoids import-time cycles with machine_control listeners.
        from backend.controllers.machine_control import ValidatedCode

        return ValidatedCode(
            id=getattr(obj, "id", None),
            code=obj.code,
            order_id=obj.order_id,
            usage_limit=obj.usage_limit,
            current_usage=obj.current_usage,
        )

    def lookup(self, identifier: str, mode: str = "local_code") -> ProviderLookupResult:
        code = (identifier or "").strip()
        if not code:
            return ProviderLookupResult(success=False, message="Missing code")

        db = self._get_session()
        try:
            obj = db.query(Code).filter_by(code=code).first()
            if not obj:
                return ProviderLookupResult(success=False, message=INVALID_CODE_MESSAGE)
            if obj.expiration_date and obj.expiration_date <= datetime.utcnow():
                return ProviderLookupResult(success=False, message=INVALID_CODE_MESSAGE)
            if obj.current_usage >= obj.usage_limit:
                return ProviderLookupResult(success=False, message=INVALID_CODE_MESSAGE)
            return ProviderLookupResult(
                success=True,
                message="",
                entitlement=self._to_validated_code(obj),
            )
        finally:
            db.close()

    def authorize(self, entitlement, machine_id: Optional[str] = None) -> ProviderAuthorizationResult:
        if entitlement is None:
            return ProviderAuthorizationResult(
                authorized=False,
                message=INVALID_CODE_MESSAGE,
                entitlement=None,
            )

        lookup_result = self.lookup(getattr(entitlement, "code", ""), mode="local_code")
        if not lookup_result.success:
            return ProviderAuthorizationResult(
                authorized=False,
                message=lookup_result.message,
                entitlement=None,
            )
        return ProviderAuthorizationResult(
            authorized=True,
            message="",
            entitlement=lookup_result.entitlement,
        )

    def commit_start(self, entitlement, quantity: int = 1) -> ProviderCommitResult:
        if entitlement is None:
            return ProviderCommitResult(
                success=False,
                message=INVALID_CODE_MESSAGE,
                uses_left=None,
                retryable=False,
            )

        db = self._get_session()
        try:
            obj = db.query(Code).filter_by(code=entitlement.code).first()
            if not obj:
                return ProviderCommitResult(
                    success=False,
                    message=INVALID_CODE_MESSAGE,
                    uses_left=None,
                    retryable=False,
                )

            obj.current_usage += max(quantity, 1)
            uses_left = max(obj.usage_limit - obj.current_usage, 0)
            if obj.current_usage >= obj.usage_limit:
                obj.expiration_date = datetime.utcnow() + timedelta(days=1)
            db.commit()
            return ProviderCommitResult(
                success=True,
                message="",
                uses_left=uses_left,
                retryable=False,
            )
        except Exception:
            db.rollback()
            logger.exception("Failed to commit local usage", extra={"code": entitlement.code})
            raise
        finally:
            db.close()

    def mark_completion(self, entitlement, machine_id: Optional[str] = None) -> ProviderCompletionResult:
        # Local mode has no external completion side effect for now.
        return ProviderCompletionResult(success=True, message="")
