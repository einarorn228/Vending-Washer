import logging
import threading
import uuid
from typing import Optional

import serial

from backend.models import session
from backend.models.setting_model import get_setting_value
from backend.services.start_orchestrator import ingest_scan

logger = logging.getLogger(__name__)


SERIAL_PORT = "/dev/ttyACM0"
SERIAL_BAUDRATE = 9600
SCAN_TIMEOUT = 1
EXPECTED_CODE_LENGTH = 8

ser = None
SERIAL_AVAILABLE = False
_serial_init_lock = threading.Lock()
_serial_initialized = False


def _looks_like_scanner_token(value: str) -> bool:
    """True for local kiosk codes, Reisa UUIDs, or 32-char hex UUIDs (no hyphens)."""

    v = (value or "").strip()
    if not v:
        return False
    try:
        uuid.UUID(v)
        return True
    except ValueError:
        pass
    if len(v) == 32 and all(c in "0123456789abcdefABCDEF" for c in v):
        return True
    if len(v) == EXPECTED_CODE_LENGTH and v.isalnum():
        return True
    return False


def _read_scanner_settings() -> tuple[str, int, int]:
    port = get_setting_value(session, "serial_port", default="/dev/ttyACM0")
    baud = get_setting_value(session, "serial_baudrate", default=9600)
    timeout = get_setting_value(session, "scan_timeout", default=1)
    return str(port), int(baud), int(timeout)


def _ensure_serial_ready() -> bool:
    global ser, SERIAL_AVAILABLE, SERIAL_PORT, SERIAL_BAUDRATE, SCAN_TIMEOUT, _serial_initialized

    with _serial_init_lock:
        if _serial_initialized:
            return SERIAL_AVAILABLE and ser is not None

        SERIAL_PORT, SERIAL_BAUDRATE, SCAN_TIMEOUT = _read_scanner_settings()
        try:
            ser = serial.Serial(
                port=SERIAL_PORT,
                baudrate=SERIAL_BAUDRATE,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=SCAN_TIMEOUT,
            )
            ser.reset_input_buffer()
            SERIAL_AVAILABLE = True
            logger.info("Serial scanner available on %s", SERIAL_PORT)
        except Exception as exc:  # pragma: no cover - depends on hardware
            logger.warning("Serial scanner not available: %s", exc)
            SERIAL_AVAILABLE = False
            ser = None
        _serial_initialized = True
        return SERIAL_AVAILABLE and ser is not None


def _valid_scan_string(value: str) -> bool:
    """Return True if the scanned string may be a local code or external entitlement id."""

    if _looks_like_scanner_token(value):
        return True
    v = (value or "").strip()
    logger.debug(
        "Ignoring scan %r: expected %d-char alphanumeric local code or UUID",
        v,
        EXPECTED_CODE_LENGTH,
    )
    return False


def _handle_scanned_value(decoded: str) -> None:
    """Invoke the shared scan handler with logging around outcomes."""

    if not _valid_scan_string(decoded):
        if decoded:
            logger.info(
                "Scanner line ignored (expected 8-char local code or UUID): %r",
                decoded[:128],
            )
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
            if raw:
                logger.info(
                    "Scanner received %d byte(s) but nothing left after decode/strip: %r",
                    len(raw),
                    raw[:64],
                )
            continue

        logger.debug("Decoded scan string: '%s'", decoded)
        _handle_scanned_value(decoded)


_scanner_thread: Optional[threading.Thread] = None
_thread_lock = threading.Lock()


def start_scanner_listener() -> None:
    """Start the scanner loop in a background daemon thread once."""

    global _scanner_thread

    if not _ensure_serial_ready():
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

    _ensure_serial_ready()
    scanner_loop()


if __name__ == "__main__":
    listen_for_scans()
