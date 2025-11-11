from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime
from backend.models import Base


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String)
    order_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    result = Column(String)
    details = Column(String)
