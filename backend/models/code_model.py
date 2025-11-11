# code_model.py

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from backend.models import Base


class Code(Base):
    __tablename__ = "codes"

    # Fields to store the QR code, order ID, usage info, and expiration date
    code = Column(String, primary_key=True)  # Unique QR code
    order_id = Column(String)  # Order ID associated with the code
    usage_limit = Column(Integer)  # Maximum number of times the code can be used
    current_usage = Column(Integer)  # Current usage count
    expiration_date = Column(
        DateTime, nullable=True
    )  # When the code becomes eligible for deletion; None means no expiration

    # Optional creation timestamp used by some admin views
    created_at = Column(DateTime, default=datetime.utcnow)
