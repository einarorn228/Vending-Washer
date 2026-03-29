from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

# Create the engine (the connection to the database)
engine = create_engine("sqlite:///codes.db", echo=False)

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
