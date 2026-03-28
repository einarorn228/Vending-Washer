"""Small provider-selection helper for local/reisa modes."""

from __future__ import annotations

from typing import Tuple

from backend.models import Session
from backend.models.setting_model import get_setting_value
from backend.providers.base_provider import BaseProvider
from backend.providers.local_provider import LocalProvider
from backend.providers.reisa_provider import ReisaProvider


def _to_bool(value: str, default: bool = False) -> bool:
    raw = (value or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _to_int(value: str, default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def resolve_provider() -> Tuple[str, BaseProvider]:
    """Resolve the active provider from settings; defaults safely to local."""

    db = Session()
    try:
        provider_default = (get_setting_value(db, "provider_default", "local") or "local").strip().lower()
        reisa_enabled = _to_bool(get_setting_value(db, "provider_reisa_enabled", "false"), default=False)
        if provider_default != "reisa" or not reisa_enabled:
            return "local", LocalProvider()

        base_url = get_setting_value(db, "reisa_base_url", "") or ""
        bearer_token = get_setting_value(db, "reisa_bearer_token", "") or ""
        connect_timeout_ms = _to_int(get_setting_value(db, "reisa_connect_timeout_ms", "1500"), 1500)
        read_timeout_ms = _to_int(get_setting_value(db, "reisa_read_timeout_ms", "2500"), 2500)
        return (
            "reisa",
            ReisaProvider(
                base_url=base_url,
                bearer_token=bearer_token,
                connect_timeout_ms=connect_timeout_ms,
                read_timeout_ms=read_timeout_ms,
            ),
        )
    finally:
        db.close()
