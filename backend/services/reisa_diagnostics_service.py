"""Operator-facing helpers for diagnosing Reisa sync problems."""

from __future__ import annotations

from typing import Any

from backend.services.reisa_audit_service import (
    list_failed_reisa_audit_events,
    list_sessions_with_external_sync_failures,
)


def get_reisa_sync_diagnostics(*, limit: int = 100) -> dict[str, list[dict[str, Any]]]:
    """Return compact diagnostic snapshots for failed Reisa sync operations."""

    bounded = max(min(int(limit), 500), 1)
    return {
        "failed_sessions": list_sessions_with_external_sync_failures(limit=bounded),
        "failed_audit_events": list_failed_reisa_audit_events(limit=bounded),
    }
