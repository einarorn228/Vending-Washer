from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create the engine (the connection to the database)
engine = create_engine("sqlite:///codes.db", echo=False)

# Base class for models
Base = declarative_base()

# Session maker
Session = sessionmaker(bind=engine)
session = Session()


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
    )


def init_db():
    """Create all tables."""
    _register_models()
    Base.metadata.create_all(bind=engine)
