"""Low-level Reisa API client."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class ReisaClientError(Exception):
    """Raised for normalized Reisa client errors."""

    message: str
    status_code: Optional[int] = None
    retryable: bool = False


class ReisaClient:
    """HTTP wrapper for Reisa lookup/info and start-commit write endpoints."""

    def __init__(
        self,
        *,
        base_url: str,
        bearer_token: str,
        connect_timeout_ms: int = 1500,
        read_timeout_ms: int = 2500,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.bearer_token = (bearer_token or "").strip()
        self.timeout = (
            max(connect_timeout_ms, 100) / 1000.0,
            max(read_timeout_ms, 100) / 1000.0,
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.bearer_token}",
        }

    def _ensure_configured(self) -> None:
        if not self.base_url:
            raise ReisaClientError("Reisa base URL is not configured", retryable=False)
        if not self.bearer_token:
            raise ReisaClientError("Reisa bearer token is not configured", retryable=False)

    def _get(self, path: str) -> Any:
        self._ensure_configured()
        url = f"{self.base_url}{path}"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        except requests.Timeout as exc:
            logger.warning("Reisa request timeout", extra={"path": path})
            raise ReisaClientError("Reisa request timed out", retryable=True) from exc
        except requests.RequestException as exc:
            logger.warning("Reisa request failed", extra={"path": path})
            raise ReisaClientError("Failed to reach Reisa", retryable=True) from exc

        if resp.status_code == 404:
            raise ReisaClientError("Reisa entitlement not found", status_code=404, retryable=False)
        if resp.status_code in (401, 403):
            raise ReisaClientError("Reisa authentication failed", status_code=resp.status_code, retryable=False)
        if resp.status_code >= 500:
            raise ReisaClientError(
                "Reisa service unavailable",
                status_code=resp.status_code,
                retryable=True,
            )
        if resp.status_code >= 400:
            raise ReisaClientError(
                "Reisa request rejected",
                status_code=resp.status_code,
                retryable=False,
            )

        try:
            return resp.json()
        except ValueError as exc:
            raise ReisaClientError("Invalid Reisa response format", retryable=False) from exc

    def _post(self, path: str, payload: Optional[dict[str, Any]] = None) -> Any:
        self._ensure_configured()
        url = f"{self.base_url}{path}"
        body = payload or {}
        try:
            resp = requests.post(url, headers=self._headers(), json=body, timeout=self.timeout)
        except requests.Timeout as exc:
            logger.warning("Reisa request timeout", extra={"path": path})
            raise ReisaClientError("Reisa request timed out", retryable=True) from exc
        except requests.RequestException as exc:
            logger.warning("Reisa request failed", extra={"path": path})
            raise ReisaClientError("Failed to reach Reisa", retryable=True) from exc

        if resp.status_code in (401, 403):
            raise ReisaClientError("Reisa authentication failed", status_code=resp.status_code, retryable=False)
        if resp.status_code >= 500:
            raise ReisaClientError(
                "Reisa service unavailable",
                status_code=resp.status_code,
                retryable=True,
            )
        if resp.status_code >= 400:
            raise ReisaClientError(
                "Reisa request rejected",
                status_code=resp.status_code,
                retryable=False,
            )

        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {}

    def get_info(self) -> Any:
        return self._get("/info")

    def get_by_uuid(self, uuid: str) -> Any:
        value = (uuid or "").strip()
        if not value:
            raise ReisaClientError("Missing UUID", retryable=False)
        return self._get(f"/uuid/{value}")

    def get_by_pin(self, pin: str) -> Any:
        value = (pin or "").strip()
        if not value:
            raise ReisaClientError("Missing PIN", retryable=False)
        return self._get(f"/pin/{value}")

    def post_status(self, uuid: str, *, action: str) -> Any:
        value = (uuid or "").strip()
        if not value:
            raise ReisaClientError("Missing UUID", retryable=False)
        action_value = (action or "").strip()
        if not action_value:
            raise ReisaClientError("Missing status action", retryable=False)
        return self._post(f"/uuid/{value}/status", {"action": action_value})

    def post_completion_status(self, uuid: str, *, action: str = "WASHING_MACHINE_COMPLETED") -> Any:
        return self.post_status(uuid, action=action)

    def post_deduct(self, uuid: str, *, quantity: int) -> Any:
        value = (uuid or "").strip()
        if not value:
            raise ReisaClientError("Missing UUID", retryable=False)
        qty = max(int(quantity), 1)
        return self._post(f"/uuid/{value}/deduct", {"quantity": qty})
