# models.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create SQLite engine
engine = create_engine('sqlite:///codes.db')
Base = declarative_base()

# Define the 'Code' table with an order_id column
class Code(Base):
    __tablename__ = 'codes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False)
    order_id = Column(String, nullable=False)  # New column to store the order ID
    usage_limit = Column(Integer, nullable=False)
    current_usage = Column(Integer, default=0)

# Create tables in the database
Base.metadata.create_all(engine)

# Set up a session to interact with the database
Session = sessionmaker(bind=engine)
session = Session()