# backend/help/cli.py
"""Compile both Help manifests.

Run after editing any guide:   python -m backend.help.cli
Verify without writing:        python -m backend.help.cli --check
"""

import json
import sys

from backend.help.artifact_paths import (
    ADMIN_ARTIFACT,
    ADMIN_ROOT,
    PUBLIC_ARTIFACT,
    PUBLIC_ROOT,
    REPO_ROOT,
    git_build_id,
)
from backend.help.compiler import compile_help
from backend.help.validator import validate_manifest


def known_setting_keys():
    from backend.services.dev_admin_service import SETTING_SCHEMA
    return set(SETTING_SCHEMA)


def build_manifest(root, trust_class):
    manifest = compile_help(root, trust_class, known_setting_keys(), build_id=None)
    validate_manifest(manifest)
    return manifest


def serialise(manifest):
    return json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_artifacts():
    for root, trust_class, artifact in (
        (ADMIN_ROOT, "admin", ADMIN_ARTIFACT),
        (PUBLIC_ROOT, "public_bootstrap", PUBLIC_ARTIFACT),
    ):
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(serialise(build_manifest(root, trust_class)), encoding="utf-8")
        print(f"wrote {artifact.relative_to(REPO_ROOT)}")


def main(argv):
    check_only = "--check" in argv
    drift = False
    for root, trust_class, artifact in (
        (ADMIN_ROOT, "admin", ADMIN_ARTIFACT),
        (PUBLIC_ROOT, "public_bootstrap", PUBLIC_ARTIFACT),
    ):
        fresh = serialise(build_manifest(root, trust_class))
        if check_only:
            current = artifact.read_text(encoding="utf-8") if artifact.exists() else ""
            if fresh != current:
                print(f"STALE: {artifact.relative_to(REPO_ROOT)}", file=sys.stderr)
                drift = True
        else:
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text(fresh, encoding="utf-8")
            print(f"wrote {artifact.relative_to(REPO_ROOT)}")
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
