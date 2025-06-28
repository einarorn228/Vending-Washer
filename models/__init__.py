from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create the engine (the connection to the database)
engine = create_engine('sqlite:///codes.db', echo=True)

# Create the base class for models to inherit
Base = declarative_base()

# Create a session for database operations
Session = sessionmaker(bind=engine)
session = Session()

# Function to create all tables
def init_db():
    Base.metadata.create_all(bind=engine)