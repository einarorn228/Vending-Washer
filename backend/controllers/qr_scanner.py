import logging
import threading
from typing import Optional

import serial

from backend.models import session
from backend.models.setting_model import get_setting_value
from backend.services.start_orchestrator import ingest_scan

logger = logging.getLogger(__name__)


SERIAL_PORT = get_setting_value(session, "serial_port", default="/dev/ttyACM0")
SERIAL_BAUDRATE = int(get_setting_value(session, "serial_baudrate", default=9600))
SCAN_TIMEOUT = int(get_setting_value(session, "scan_timeout", default=1))
EXPECTED_CODE_LENGTH = 8

ser = None
SERIAL_AVAILABLE = False

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
    logger.info("Serial scanner available on %s", SERIAL_PORT)
except Exception as exc:  # pragma: no cover - depends on hardware
    logger.warning("Serial scanner not available: %s", exc)


def _valid_scan_string(value: str) -> bool:
    """Return True if the scanned string meets basic expectations."""

    if len(value) < EXPECTED_CODE_LENGTH:
        logger.debug("Ignoring scan '%s': reason=too short", value)
        return False
    if len(value) > EXPECTED_CODE_LENGTH:
        logger.debug("Ignoring scan '%s': reason=too long", value)
        return False
    if not value.isalnum():
        logger.debug("Ignoring scan '%s': reason=invalid format", value)
        return False
    return True


def _handle_scanned_value(decoded: str) -> None:
    """Invoke the shared scan handler with logging around outcomes."""

    if not _valid_scan_string(decoded):
        return

    try:
        outcome = ingest_scan(decoded, source="scanner")
        if outcome.success:
            logger.info("Accepted scan: %s", decoded)
        else:
            logger.debug("Scan rejected: %s (reason=%s)", decoded, outcome.message)
    except Exception as exc:  # pragma: no cover - defensive for runtime issues
        logger.exception("Error processing QR code: %s", exc)


def scanner_loop() -> None:
    """Continuously read from the serial scanner and process scans."""

    if not SERIAL_AVAILABLE:
        logger.warning("Scanner loop not started: serial unavailable")
        return

    logger.info("Starting scanner loop on %s", SERIAL_PORT)

    while True:
        try:
            raw = ser.readline()
        except Exception as exc:  # pragma: no cover - depends on hardware
            logger.error("Error reading from scanner: %s", exc)
            continue

        if not raw:
            continue

        logger.debug("Raw scan bytes: %r", raw)

        decoded = raw.decode("utf-8", errors="ignore").strip()
        if not decoded:
            continue

        logger.debug("Decoded scan string: '%s'", decoded)
        _handle_scanned_value(decoded)


_scanner_thread: Optional[threading.Thread] = None
_thread_lock = threading.Lock()


def start_scanner_listener() -> None:
    """Start the scanner loop in a background daemon thread once."""

    global _scanner_thread

    if not SERIAL_AVAILABLE:
        logger.warning("Scanner listener not started because serial is unavailable")
        return

    with _thread_lock:
        if _scanner_thread and _scanner_thread.is_alive():
            logger.debug("Scanner listener already running")
            return

        _scanner_thread = threading.Thread(
            target=scanner_loop,
            name="qr-scanner-listener",
            daemon=True,
        )
        _scanner_thread.start()
        logger.info("Scanner listener thread started on %s", SERIAL_PORT)


def listen_for_scans() -> None:
    """Backward-compatible entrypoint to run the scanner loop in the foreground."""

    scanner_loop()


if __name__ == "__main__":
    listen_for_scans()
