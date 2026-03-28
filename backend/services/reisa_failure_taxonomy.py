"""Normalized error categories for Reisa sync diagnostics."""

from __future__ import annotations

from typing import Optional


def classify_reisa_failure(
    *,
    request_type: Optional[str],
    status_code: Optional[int],
    error_message: Optional[str],
    result: Optional[str],
    retryable: bool,
) -> Optional[str]:
    """Return a normalized failure category while preserving raw error details elsewhere."""

    if (result or "").strip().lower() != "error":
        return None

    code = int(status_code) if isinstance(status_code, int) else None
    msg = (error_message or "").strip().lower()
    action = (request_type or "").strip().lower()

    if "manual_skip" in msg or "skipped" in msg:
        return "manual_skip"
    if "already synced" in msg or "already_synced" in msg or "already synced" in msg:
        return "already_synced"
    if "invalid action" in msg or "unsupported action" in msg:
        return "invalid_action"
    if "invalid reference" in msg or "missing_uuid_token" in msg or "missing_reisa_entitlement" in msg:
        return "invalid_reference"
    if "timeout" in msg or "timed out" in msg:
        return "network_timeout"
    if "connection refused" in msg or "connection reset" in msg or "name resolution" in msg:
        return "network_unreachable"
    if "unauthorized" in msg or "forbidden" in msg or "auth" in msg:
        return "auth_failed"
    if "invalid response" in msg or "unexpected response" in msg:
        return "unexpected_response"

    if code is not None:
        if code in {401, 403}:
            return "auth_failed"
        if code == 404:
            return "invalid_reference"
        if 400 <= code < 500:
            if action in {"start_status", "completion_status"}:
                return "invalid_action"
            return "invalid_reference"
        if 500 <= code < 600:
            return "server_5xx"

    if retryable:
        return "unexpected_response"
    return "manual_skip"
