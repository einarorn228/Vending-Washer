"""Shared test-database isolation.

Imported by both ``backend/tests/__init__.py`` (covers ``python -m unittest
backend.tests.<module>``) and ``backend/tests/conftest.py`` (covers pytest). Whichever
runs first wins; the other is a no-op.

This must take effect before any ``backend.models`` import, because the SQLAlchemy
engine is created at module import time.
"""

import atexit
import os
import shutil
import tempfile

ENV_VAR = "VENDING_WASHER_DATABASE_URL"


def use_throwaway_database() -> str:
    """Point the backend engine at a temporary SQLite file for this process."""
    existing = os.environ.get(ENV_VAR)
    if existing:
        return existing

    tmp_dir = tempfile.mkdtemp(prefix="vending-washer-tests-")
    atexit.register(shutil.rmtree, tmp_dir, True)
    url = "sqlite:///" + os.path.join(tmp_dir, "codes.db")
    os.environ[ENV_VAR] = url
    return url
