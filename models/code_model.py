from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime, timedelta
from models import Base

class Code(Base):
    __tablename__ = 'codes'

    # Fields to store the QR code, order ID, usage info, and expiration date
    code = Column(String, primary_key=True)               # Unique QR code
    order_id = Column(String)                             # Order ID associated with the code
    usage_limit = Column(Integer)                         # Maximum number of times the code can be used
    current_usage = Column(Integer)                       # Current usage count
    expiration_date = Column(DateTime, nullable=True)     # Expiration date after full usage

    def set_expiration(self, days):
        """Set expiration date X days from now."""
        self.expiration_date = datetime.now() + timedelta(days=days)