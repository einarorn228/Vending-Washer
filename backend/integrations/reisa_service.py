"""Reisa service adapter for entitlement normalization and start-commit writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from backend.integrations.reisa_client import ReisaClient, ReisaClientError


@dataclass
class ReisaServiceError(Exception):
    message: str
    retryable: bool = False


@dataclass
class ReisaEntitlement:
    provider: str
    lookup_mode: str
    external_id: str
    code: str
    order_id: Optional[str]
    usage_limit: int
    current_usage: int
    uses_left: int
    transaction_number: Optional[str]
    booking_number: Optional[str]
    service_id: Optional[str]
    token: Optional[str]
    pin_code: Optional[str]
    customer_name: Optional[str]
    customer_email: Optional[str]
    metadata_last_used: Optional[str]
    raw: dict[str, Any]


@dataclass
class ReisaCommitStartResult:
    uses_left: Optional[int]
    raw: dict[str, Any]


class ReisaService:
    """Maps raw Reisa payloads into app-friendly entitlement shapes."""

    def __init__(self, client: ReisaClient) -> None:
        self.client = client

    def get_info(self) -> Any:
        try:
            return self.client.get_info()
        except ReisaClientError as exc:
            raise ReisaServiceError(exc.message, retryable=exc.retryable) from exc

    def lookup_by_uuid(self, uuid: str) -> ReisaEntitlement:
        return self._normalize_lookup(self.client.get_by_uuid(uuid), mode="uuid", identifier=uuid)

    def lookup_by_pin(self, pin: str) -> ReisaEntitlement:
        return self._normalize_lookup(self.client.get_by_pin(pin), mode="pin", identifier=pin)

    def lookup_auto(self, identifier: str) -> ReisaEntitlement:
        value = (identifier or "").strip()
        if not value:
            raise ReisaServiceError("Missing code", retryable=False)

        # Prefer UUID-formatted values first; fallback to PIN lookup.
        if self._looks_like_uuid(value):
            try:
                return self.lookup_by_uuid(value)
            except ReisaClientError as exc:
                if exc.status_code != 404:
                    raise ReisaServiceError(exc.message, retryable=exc.retryable) from exc
        try:
            return self.lookup_by_pin(value)
        except ReisaClientError as exc:
            raise ReisaServiceError(exc.message, retryable=exc.retryable) from exc

    def post_start_status(self, uuid: str, *, action: str = "WASHING_MACHINE_START") -> dict[str, Any]:
        try:
            payload = self.client.post_status(uuid, action=action)
        except ReisaClientError as exc:
            raise ReisaServiceError(exc.message, retryable=exc.retryable) from exc
        if isinstance(payload, dict):
            return payload
        return {}

    def deduct_usage(self, uuid: str, *, quantity: int = 1) -> ReisaCommitStartResult:
        try:
            payload = self.client.post_deduct(uuid, quantity=quantity)
        except ReisaClientError as exc:
            raise ReisaServiceError(exc.message, retryable=exc.retryable) from exc

        normalized_payload = payload if isinstance(payload, dict) else {}
        uses_left = self._extract_remaining_quantity(normalized_payload)
        return ReisaCommitStartResult(uses_left=uses_left, raw=normalized_payload)

    @staticmethod
    def _looks_like_uuid(value: str) -> bool:
        try:
            from uuid import UUID

            UUID(value)
            return True
        except Exception:
            return False

    def _normalize_lookup(self, payload: Any, *, mode: str, identifier: str) -> ReisaEntitlement:
        if not isinstance(payload, dict):
            raise ReisaServiceError("Unexpected Reisa payload", retryable=False)

        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        customer = payload.get("customer") if isinstance(payload.get("customer"), dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

        total = self._as_non_negative_int(details.get("totalQuantity"))
        used = self._as_non_negative_int(details.get("usedQuantity"))
        used = min(used, total)
        uses_left = max(total - used, 0)

        provider_reference = (
            self._first_non_empty(
                payload.get("transactionNumber"),
                payload.get("bookingNumber"),
                payload.get("serviceId"),
                payload.get("token"),
                payload.get("pinCode"),
                identifier,
            )
            or identifier
        )

        return ReisaEntitlement(
            provider="reisa",
            lookup_mode=mode,
            external_id=provider_reference,
            code=identifier,
            order_id=payload.get("bookingNumber") or payload.get("transactionNumber"),
            usage_limit=total,
            current_usage=used,
            uses_left=uses_left,
            transaction_number=payload.get("transactionNumber"),
            booking_number=payload.get("bookingNumber"),
            service_id=payload.get("serviceId"),
            token=payload.get("token"),
            pin_code=payload.get("pinCode"),
            customer_name=customer.get("name"),
            customer_email=customer.get("email"),
            metadata_last_used=self._as_iso_str_or_none(metadata.get("lastUsed")),
            raw=payload,
        )

    @staticmethod
    def _as_non_negative_int(value: Any) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return 0
        return max(number, 0)

    @staticmethod
    def _first_non_empty(*values: Any) -> Optional[str]:
        for value in values:
            text = str(value).strip() if value is not None else ""
            if text:
                return text
        return None

    @staticmethod
    def _as_iso_str_or_none(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        # Keep original external value while sanity-checking it is datetime-like.
        try:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
        return text

    @classmethod
    def _extract_remaining_quantity(cls, payload: dict[str, Any]) -> Optional[int]:
        for key in ("remainingQuantity", "remaining", "usesLeft"):
            value = payload.get(key)
            if value is not None:
                return cls._as_non_negative_int(value)

        details = payload.get("details")
        if isinstance(details, dict):
            total = details.get("totalQuantity")
            used = details.get("usedQuantity")
            if total is not None and used is not None:
                return max(cls._as_non_negative_int(total) - cls._as_non_negative_int(used), 0)

        total = payload.get("totalQuantity")
        used = payload.get("usedQuantity")
        if total is not None and used is not None:
            return max(cls._as_non_negative_int(total) - cls._as_non_negative_int(used), 0)
        return None
