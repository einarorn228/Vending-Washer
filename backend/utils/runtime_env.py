"""Runtime environment detection.

Used to keep automated test runs away from real operator data: the SQLite database
(``backend/models``) and ``frontend/.env`` (``backend/controllers/dev_admin_api``).
"""

import os
import sys


def running_under_tests() -> bool:
    """True when this process is an automated test run, not the kiosk runtime."""
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_VERSION"):
        return True
    if "pytest" in sys.modules:
        return True
    argv0 = sys.argv[0] if sys.argv else ""
    name = os.path.basename(argv0)
    if name in {"pytest", "py.test"} or name.startswith("pytest"):
        return True
    # `python -m unittest ...` rewrites sys.argv[0] to this exact literal.
    if argv0 == "python -m unittest":
        return True
    # `python path/to/test_foo.py`
    if name.startswith("test_") and name.endswith(".py"):
        return True

    main_file = getattr(sys.modules.get("__main__"), "__file__", "") or ""
    main_file = os.path.normpath(main_file)
    # Belt and braces for runners that leave argv[0] as the stdlib entry point.
    if main_file.endswith(os.path.join("unittest", "__main__.py")):
        return True
    if main_file.endswith(os.path.join("pytest", "__main__.py")):
        return True
    if os.path.basename(main_file).startswith("test_"):
        return True
    return False
