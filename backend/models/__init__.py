import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from backend.utils.runtime_env import running_under_tests

# The default resolves relative to the working directory, so the kiosk keeps using
# codes.db in the repository root. Tests override this to a throwaway file (see
# backend/tests/_isolation.py) so running the suite never touches the real database.
DATABASE_URL = os.environ.get("VENDING_WASHER_DATABASE_URL", "sqlite:///codes.db")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sqlite_path(url: str):
    """Absolute filesystem path for a SQLite URL, or None for other backends."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return None
    raw = url[len(prefix) :]
    if not raw or raw == ":memory:":
        return None
    return os.path.realpath(raw)


def _assert_not_production_database(url: str) -> None:
    """Refuse to bind a test run to the operator's real database.

    Test ``setUp`` methods delete rows from ``settings``, ``machines`` and ``devices``.
    Reaching the real ``codes.db`` wipes the runtime configuration (including
    ``api_key``), so abort loudly instead of silently destroying it.
    """
    if not running_under_tests():
        return
    resolved = _sqlite_path(url)
    if resolved is None:
        return
    protected = {
        os.path.realpath(os.path.join(_REPO_ROOT, "codes.db")),
        os.path.realpath(os.path.join(os.getcwd(), "codes.db")),
    }
    if resolved in protected:
        raise RuntimeError(
            "Refusing to run tests against the real application database at "
            f"{resolved}. Test setUp deletes settings/machines/devices rows and would "
            "destroy the runtime configuration. Set VENDING_WASHER_DATABASE_URL to a "
            "throwaway path, or run the suite via `python -m pytest backend/tests/` "
            "(backend/tests/_isolation.py does this automatically)."
        )


_assert_not_production_database(DATABASE_URL)

# Create the engine (the connection to the database)
engine = create_engine(DATABASE_URL, echo=False)

# Base class for models
Base = declarative_base()

# Session factory for explicit short-lived sessions.
Session = sessionmaker(bind=engine)
# Thread-local scoped session proxy used across existing call sites.
ScopedSession = scoped_session(Session)
# Backwards-compatible session proxy used across the codebase.
session = ScopedSession


def _register_models() -> None:
    # Import model modules so SQLAlchemy metadata is fully populated before create_all.
    from backend.models import (  # noqa: F401
        code_model,
        device_model,
        machine_model,
        scan_log_model,
        setting_model,
        settings_audit_model,
        usage_session_model,
        reisa_audit_model,
        reisa_retry_job_model,
    )


def init_db():
    """Create all tables."""
    _register_models()
    Base.metadata.create_all(bind=engine)


def remove_session() -> None:
    """Remove current thread/app-context scoped session."""
    ScopedSession.remove()
