"""Seed data for devices and machines to support telemetry-driven control."""

from __future__ import annotations

import logging
from typing import Dict, Optional

from sqlalchemy.orm import Session as SASession

from backend.models import Session, init_db
from backend.models.device_model import Device
from backend.models.machine_model import Machine, MachineConfig

init_db()


DEFAULT_DEVICES = [
    {
        "name": "Button Box",
        "role": "button_box",
        "model": "shelly-1",
        "ip": "192.168.107.10",
        "relay_channel": 0,
        "metric_source": "none",
    },
    {
        "name": "i4 Front",
        "role": "i4",
        "model": "shelly-plus-i4",
        "ip": "192.168.107.15",
        "input_channel": 0,
        "metric_source": "digital",
    },
    {
        "name": "Washer 1 UNI",
        "role": "washer_uni",
        "model": "shelly-uni",
        "ip": "192.168.107.11",
        "relay_channel": 0,
        "metric_source": "voltage",
    },
    {
        "name": "Dryer 1 UNI",
        "role": "dryer_uni",
        "model": "shelly-uni",
        "ip": "192.168.107.12",
        "relay_channel": 0,
        "metric_source": "voltage",
    },
    {
        "name": "Washer 2 UNI",
        "role": "washer_uni",
        "model": "shelly-uni",
        "ip": "192.168.107.13",
        "relay_channel": 0,
        "metric_source": "power",
    },
    {
        "name": "Dryer 2 UNI",
        "role": "dryer_uni",
        "model": "shelly-uni",
        "ip": "192.168.107.14",
        "relay_channel": 0,
        "metric_source": "power",
    },
]


DEFAULT_MACHINES = [
    {
        "name": "washer1",
        "ui_name": "Washer 1",
        "uni_device_name": "Washer 1 UNI",
        "i4_button_index": 0,
    },
    {
        "name": "dryer1",
        "ui_name": "Dryer 1",
        "uni_device_name": "Dryer 1 UNI",
        "i4_button_index": 1,
    },
    {
        "name": "washer2",
        "ui_name": "Washer 2",
        "uni_device_name": "Washer 2 UNI",
        "i4_button_index": 2,
    },
    {
        "name": "dryer2",
        "ui_name": "Dryer 2",
        "uni_device_name": "Dryer 2 UNI",
        "i4_button_index": 3,
    },
]


DEFAULT_CONFIG = {
    "on_threshold": 8,
    "off_threshold": 3,
    "on_confirm_ms": 1200,
    "off_confirm_ms": 3000,
    "poll_interval_ms": 1000,
}


def _get_device_map(db: SASession) -> Dict[str, Device]:
    devices = db.query(Device).all()
    return {device.name: device for device in devices}


def seed_devices(logger: Optional[logging.Logger] = None) -> None:
    db = Session()
    log = logger or logging.getLogger(__name__)
    try:
        existing = db.query(Device).count()
        if existing:
            return
        for payload in DEFAULT_DEVICES:
            device = Device(**payload)
            db.add(device)
        db.commit()
        log.info("Seeded default devices")
    except Exception:
        db.rollback()
        log.exception("Failed seeding default devices")
        raise
    finally:
        db.close()


def seed_machines(logger: Optional[logging.Logger] = None) -> None:
    db = Session()
    log = logger or logging.getLogger(__name__)
    try:
        if db.query(Machine).count():
            return

        devices = _get_device_map(db)
        i4_device = (
            db.query(Device)
            .filter(Device.role == "i4")
            .order_by(Device.id.asc())
            .first()
        )

        for payload in DEFAULT_MACHINES:
            uni_device = devices.get(payload["uni_device_name"])
            if not uni_device:
                log.warning(
                    "Skipping machine seed; missing device", extra={"machine": payload}
                )
                continue
            machine = Machine(
                name=payload["name"],
                ui_name=payload["ui_name"],
                uni_device_id=uni_device.id,
                uni_relay_channel=uni_device.relay_channel,
                i4_device_id=i4_device.id if i4_device else None,
                i4_button_index=payload["i4_button_index"],
                is_enabled=1,
            )
            db.add(machine)
            db.flush()
            config = MachineConfig(machine_id=machine.id, **DEFAULT_CONFIG)
            db.add(config)

        db.commit()
        log.info("Seeded default machines and configs")
    except Exception:
        db.rollback()
        log.exception("Failed seeding machines")
        raise
    finally:
        db.close()


def bootstrap_devices_and_machines(logger: Optional[logging.Logger] = None) -> None:
    seed_devices(logger=logger)
    seed_machines(logger=logger)


if __name__ == "__main__":
    bootstrap_devices_and_machines()

