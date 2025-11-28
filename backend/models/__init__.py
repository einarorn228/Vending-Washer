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


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
