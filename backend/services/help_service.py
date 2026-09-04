# backend/services/help_service.py
"""Load the compiled Help manifest once, behind a failure boundary.

Help is a support feature; the kiosk is the product. A missing, malformed, or
version-incompatible manifest must degrade Help alone -- it must never raise into
backend import, the telemetry loop, scanning, or machine control.
"""

import hashlib
import json
import logging

from backend.help.artifact_paths import ADMIN_ARTIFACT, git_build_id
from backend.help.schema import SCHEMA_VERSION

logger = logging.getLogger(__name__)

_cache = None          # None = not yet attempted
_status = None
_digest = None


def _read_artifact():
    return ADMIN_ARTIFACT.read_text(encoding="utf-8")


def _load():
    global _cache, _status, _digest
    try:
        raw = _read_artifact()
        payload = json.loads(raw)
        _digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    except FileNotFoundError:
        _cache, _status = None, {"available": False, "reason": "manifest_missing"}
        logger.error("Help manifest missing at %s; Help disabled, backend unaffected", ADMIN_ARTIFACT)
        return
    except (OSError, ValueError) as exc:
        _cache, _status = None, {"available": False, "reason": "manifest_unreadable"}
        logger.error("Help manifest unreadable (%s); Help disabled, backend unaffected", exc)
        return
    except Exception as exc:  # pragma: no cover - defensive, must never escape
        _cache, _status = None, {"available": False, "reason": "manifest_unreadable"}
        logger.exception("Unexpected Help manifest failure (%s); Help disabled", exc)
        return

    if not isinstance(payload, dict):
        _cache, _status = None, {
            "available": False,
            "reason": "manifest_unreadable",
            "detail": f"top-level JSON value is {type(payload).__name__}, expected object",
        }
        logger.error(
            "Help manifest top-level value is %s, expected object; Help disabled, backend unaffected",
            type(payload).__name__,
        )
        return

    if payload.get("schema_version") != SCHEMA_VERSION:
        _cache, _status = None, {
            "available": False,
            "reason": "schema_version_unsupported",
            "found_schema_version": payload.get("schema_version"),
        }
        logger.error("Help manifest schema %s != supported %s; Help disabled",
                     payload.get("schema_version"), SCHEMA_VERSION)
        return

    guides = payload.get("guides")
    if not isinstance(guides, dict):
        _cache, _status = None, {
            "available": False,
            "reason": "manifest_unreadable",
            "detail": f"guides is {type(guides).__name__}, expected object",
        }
        logger.error(
            "Help manifest 'guides' is %s, expected object; Help disabled, backend unaffected",
            type(guides).__name__,
        )
        return

    _cache = payload
    _status = {
        "available": True,
        "schema_version": payload["schema_version"],
        "guide_count": payload.get("guide_count", 0),
        "locales": payload.get("locales", []),
        "default_locale": payload.get("default_locale"),
        "build_id": git_build_id(),
    }


def _ensure():
    if _status is None:
        _load()


def reset_cache():
    global _cache, _status, _digest
    _cache, _status, _digest = None, None, None


def get_manifest():
    _ensure()
    return _cache


def get_status():
    _ensure()
    return dict(_status)


def get_guide(guide_id):
    manifest = get_manifest()
    if not manifest:
        return None
    return manifest.get("guides", {}).get(guide_id)


def get_provenance():
    """Which knowledge version a support report or AI citation was built from."""
    _ensure()
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_digest": _digest,
        "build_id": git_build_id(),
    }
