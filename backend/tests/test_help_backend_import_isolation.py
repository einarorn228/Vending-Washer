# backend/tests/test_help_backend_import_isolation.py
"""Regression test: importing the backend must never require `mistune`.

`backend/services/help_service.py` used to do
`from backend.help.cli import ADMIN_ARTIFACT, git_build_id`, and `backend.help.cli`
imports `backend.help.compiler`, which imports `backend.help.blocks`, which imports
`mistune`. `mistune` is a compile-time dependency of the guide-authoring CLI only --
nothing at runtime parses Markdown. If `mistune` is missing (e.g. a minimal Pi
image), the entire backend must still import and start; Help degrades alone, as
`help_service`'s own docstring promises.

This test proves the property rather than just the current import list: it blocks
`mistune` with a `sys.meta_path` hook in a *fresh subprocess* (so no module already
cached by the rest of the test suite can hide the bug) and then imports
`backend.flask_server`, which transitively imports `help_service`.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPT = """
import sys

class _BlockMistune:
    def find_spec(self, name, path, target=None):
        if name == "mistune" or name.startswith("mistune."):
            raise ImportError("mistune intentionally blocked for this test")
        return None

sys.meta_path.insert(0, _BlockMistune())

import backend.flask_server  # noqa: F401 -- must succeed without mistune
print("IMPORT_OK")
"""


class BackendImportIsolationTests(unittest.TestCase):
    def test_backend_imports_with_mistune_unavailable(self):
        tmp_dir = tempfile.mkdtemp(prefix="vending-washer-import-isolation-")
        env = dict(os.environ)
        env["VENDING_WASHER_DATABASE_URL"] = "sqlite:///" + os.path.join(tmp_dir, "codes.db")
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [sys.executable, "-c", _SCRIPT],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(
            result.returncode, 0,
            msg=(
                "importing backend.flask_server must not require mistune "
                f"(compile-time-only dependency of backend.help.cli):\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            ),
        )
        self.assertIn("IMPORT_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
