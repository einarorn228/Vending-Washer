import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import serial
import time
from backend.models import session
from backend.models.code_model import Code
from backend.models.setting_model import get_setting_value
from backend.utils.shelly_control import send_shelly_pulse, send_shelly_on
from datetime import datetime, timedelta
import logging

from backend.utils.logger import get_error_logger, get_event_logger
from backend.controllers.machine_control import write_scan_log
from backend.metrics import inc, observe_ms

logger = logging.getLogger(__name__)
events_logger = get_event_logger()
error_logger = get_error_logger()


# ----- SETTINGS from DB -----
SERIAL_PORT = get_setting_value(session, "serial_port", default="/dev/ttyUSB0")
SERIAL_BAUDRATE = int(get_setting_value(session, "serial_baudrate", default=9600))
SCAN_TIMEOUT = int(get_setting_value(session, "scan_timeout", default=1))
SHELLY_IP = get_setting_value(session, "shelly_ip", default="192.168.1.100")
PULSE_DURATION = int(get_setting_value(session, "pulse_duration", default=1))
RELAY_MODE = get_setting_value(
    session, "relay_mode", default="on"
).lower()  # "on" or "pulse"

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


def search_table(scanned_code):
    code_entry = session.query(Code).filter_by(code=scanned_code).first()
    if not code_entry:
        return False, "Invalid code"

    # Check expiration date if present
    if code_entry.expiration_date and code_entry.expiration_date <= datetime.utcnow():
        return False, "Expired code"

    if code_entry.current_usage < code_entry.usage_limit:
        return True, code_entry

    return False, "Usage limit exceeded"


def log_scan_event(code_value, result, details=None, order_id=None):
    """Persist a scan attempt using the shared logging helper."""

    try:
        if order_id is None and code_value:
            code_entry = session.query(Code).filter_by(code=code_value).first()
            order_id = code_entry.order_id if code_entry else None
    except Exception:
        session.rollback()
        logger.exception("Failed to load order id for scan log")
        order_id = None
    write_scan_log(code_value, order_id, result, "serial", details=details)


def process_qr_code(scanned_code):
    """Validate code, then trigger Shelly according to mode."""
    try:
        is_valid, code_info = search_table(scanned_code)
        if not is_valid:
            logger.warning(
                "Invalid code", extra={"code": scanned_code, "reason": code_info}
            )
            reason_key = "invalid"
            if code_info == "Usage limit exceeded":
                reason_key = "usage_limit_exceeded"
            elif code_info == "Expired code":
                reason_key = "expired"
            events_logger.info(
                "SCAN received",
                extra={
                    "source": "scanner",
                    "code": scanned_code,
                    "result": "invalid",
                    "reason": reason_key,
                },
            )
            inc("scan_total", outcome="rejected", reason=reason_key, source="scanner")
            log_scan_event(scanned_code, "invalid", code_info)
            return

        logger.info("Code accepted")
        events_logger.info(
            "SCAN received",
            extra={"source": "scanner", "code": scanned_code, "result": "valid"},
        )
        inc("scan_total", outcome="accepted", source="scanner")

        # Simulate Shelly success if SHELLY_IP is 0 or None and debug mode is on
        debug_mode = logger.isEnabledFor(logging.DEBUG)
        if (not SHELLY_IP or SHELLY_IP == "0") and debug_mode:
            logger.debug("Simulating Shelly success (debug mode, no SHELLY_IP)")
            success = 1
        else:
            if RELAY_MODE == "pulse":
                logger.debug("Pulse mode: ON\u2192wait\u2192OFF")
                success = send_shelly_pulse(SHELLY_IP, duration=PULSE_DURATION)
            elif RELAY_MODE == "on":
                logger.debug("ON-only mode")
                success = send_shelly_on(SHELLY_IP)
            else:
                logger.error("Unknown relay mode: %s", RELAY_MODE)
                log_scan_event(
                    scanned_code, "error", f"Unknown relay mode: {RELAY_MODE}"
                )
                return

        if success:
            code_info.current_usage += 1
            if code_info.current_usage >= code_info.usage_limit:
                # Mark code for cleanup after retention period
                try:
                    days = int(
                        get_setting_value(
                            session, "expired_code_cleanup_days", default=30
                        )
                    )
                except (TypeError, ValueError):
                    days = 30
                expire_at = datetime.utcnow()
                if days and days > 0:
                    expire_at = expire_at + timedelta(days=days)
                code_info.expiration_date = expire_at

            session.commit()
            logger.info("Shelly command succeeded", extra={"code": code_info.code})
            log_scan_event(scanned_code, "valid")
            inc("scan_total", outcome="success", source="scanner")
        else:
            logger.error("Shelly command failed", extra={"code": code_info.code})
            inc("scan_total", outcome="error", reason="shelly_failed", source="scanner")
            log_scan_event(scanned_code, "invalid", "Shelly command failed")
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
        log_scan_event(scanned_code, "invalid", str(e))


def listen_for_scans():
    """Continuously get codes from scanner or input."""
    while True:
        events_logger.info("SCAN started")
        scanned_code = read_qr_code()
        logger.debug("Scanned code received", extra={"code": scanned_code})
        process_qr_code(scanned_code)


if __name__ == "__main__":
    listen_for_scans()
