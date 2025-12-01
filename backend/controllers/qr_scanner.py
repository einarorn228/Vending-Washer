import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import logging
import serial
import time

from backend.controllers.machine_control import handle_scanned_code, write_scan_log
from backend.metrics import inc, observe_ms
from backend.models import session
from backend.models.setting_model import get_setting_value
from backend.utils.logger import get_error_logger, get_event_logger

logger = logging.getLogger(__name__)
events_logger = get_event_logger()
error_logger = get_error_logger()


# ----- SETTINGS from DB -----
SERIAL_PORT = get_setting_value(session, "serial_port", default="/dev/ttyUSB0")
SERIAL_BAUDRATE = int(get_setting_value(session, "serial_baudrate", default=9600))
SCAN_TIMEOUT = int(get_setting_value(session, "scan_timeout", default=1))

# ----- Initialize serial scanner if available -----
try:
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=SERIAL_BAUDRATE,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=SCAN_TIMEOUT,
    )
    SERIAL_AVAILABLE = True

    logger.debug("Serial scanner available on %s", SERIAL_PORT)

except Exception as e:
    SERIAL_AVAILABLE = False
    logger.warning("Serial scanner not available: %s", e)


def read_qr_code():
    """Reads a QR code—serial if connected, otherwise manual input."""
    if SERIAL_AVAILABLE:
        try:
            t0 = time.perf_counter()
            data = ser.readline().decode("utf-8").strip()
            read_ms = int((time.perf_counter() - t0) * 1000)
            observe_ms("scanner_read_ms", read_ms, source="serial")
            if data:
                logger.info("Received QR Code", extra={"code": data})
                return data
        except Exception:
            logger.exception("Serial read error")
    # Fallback to manual typing
    return input("Enter code manually: ")


def process_qr_code(scanned_code):
    """Validate code and arm it for button-based machine selection."""

    try:
        success, message, _ = handle_scanned_code(scanned_code, source="scanner")
        if success:
            logger.info("Code accepted and armed", extra={"code": scanned_code})
        else:
            logger.warning(
                "Scan rejected", extra={"code": scanned_code, "message": message}
            )
    except Exception as e:
        logger.exception("Error processing QR code")
        events_logger.error(
            "SCAN error",
            extra={"code": scanned_code, "error": str(e)},
        )
        error_logger.error(
            "SCAN error while processing code",
            extra={"code": scanned_code},
            exc_info=True,
        )
        inc("scan_total", outcome="error", reason="exception", source="scanner")
        write_scan_log(scanned_code or "", None, "invalid", "scanner", details=str(e))


def listen_for_scans():
    """Continuously get codes from scanner or input."""
    while True:
        events_logger.info("SCAN started")
        scanned_code = read_qr_code()
        logger.debug("Scanned code received", extra={"code": scanned_code})
        process_qr_code(scanned_code)


if __name__ == "__main__":
    listen_for_scans()
