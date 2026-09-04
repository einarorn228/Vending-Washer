# backend/help/artifact_paths.py
"""Dependency-free constants and helpers shared by the Help CLI and the runtime service.

This module MUST NOT import the Markdown compiler (`backend.help.compiler` /
`backend.help.blocks`) or anything that pulls in `mistune`. `mistune` is a
compile-time dependency of the guide-authoring CLI only -- nothing at runtime
parses Markdown. `backend/services/help_service.py` imports from here (not from
`backend.help.cli`) so that a machine without `mistune` installed can still start
the backend; Help degrades alone, as the module's own docstring promises.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADMIN_ROOT = REPO_ROOT / "docs" / "admin-guides"
PUBLIC_ROOT = REPO_ROOT / "docs" / "public-help"
ADMIN_ARTIFACT = REPO_ROOT / "backend" / "help" / "generated" / "admin-help-manifest.json"
PUBLIC_ARTIFACT = REPO_ROOT / "frontend" / "src" / "generated" / "public-help-manifest.json"


def git_build_id():
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None
