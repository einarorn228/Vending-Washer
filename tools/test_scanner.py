"""Lightweight helper to read scans directly from the serial device."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import serial

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.utils.logger import configure_logger
from backend.models import session
from backend.models.setting_model import get_setting_value

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logger()

    port = get_setting_value(session, "serial_port", default="/dev/ttyACM0")
    baudrate = int(get_setting_value(session, "serial_baudrate", default=9600))
    timeout = int(get_setting_value(session, "scan_timeout", default=1))

    logger.info("Opening serial scanner on %s (baudrate=%s, timeout=%ss)", port, baudrate, timeout)

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - requires hardware
        logger.error("Unable to open serial port %s: %s", port, exc)
        return

    logger.info("Listening for scans. Press Ctrl+C to exit.")
    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue

            decoded = raw.decode("utf-8", errors="ignore").strip()
            print(f"RAW: {raw!r}")
            print(f"DECODED: '{decoded}'\n")
    except KeyboardInterrupt:
        logger.info("Scanner test stopped by user")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
