"""Machine model mapping UI-visible machines to devices."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.models import Base


class Machine(Base):
    """A logical machine (washer/dryer) that users interact with."""

    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    ui_name = Column(String, nullable=False)
    uni_device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    uni_relay_channel = Column(Integer)
    i4_device_id = Column(Integer, ForeignKey("devices.id"))
    i4_button_index = Column(Integer)
    is_enabled = Column(Integer, nullable=False, default=1)

    uni_device = relationship("Device", foreign_keys=[uni_device_id])
    i4_device = relationship("Device", foreign_keys=[i4_device_id])
    config = relationship("MachineConfig", back_populates="machine", uselist=False)


class MachineConfig(Base):
    """Per-machine telemetry thresholds and debounce configuration."""

    __tablename__ = "machine_configs"

    machine_id = Column(Integer, ForeignKey("machines.id"), primary_key=True)
    on_threshold = Column(Integer, nullable=False)
    off_threshold = Column(Integer, nullable=False)
    on_confirm_ms = Column(Integer, nullable=False, default=1200)
    off_confirm_ms = Column(Integer, nullable=False, default=3000)
    poll_interval_ms = Column(Integer, nullable=False, default=1000)

    machine = relationship("Machine", back_populates="config")

