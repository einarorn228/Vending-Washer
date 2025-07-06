import serial
from models import session
from models.code_model import Code
from models.scan_log_model import ScanLog
from models.setting_model import get_setting_value
from utils.shelly_control import send_shelly_pulse, send_shelly_on
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


# ----- SETTINGS from DB -----
SERIAL_PORT     = get_setting_value(session, "serial_port",    default="/dev/ttyUSB0")
SERIAL_BAUDRATE = int(get_setting_value(session, "serial_baudrate", default=9600))
SCAN_TIMEOUT    = int(get_setting_value(session, "scan_timeout",    default=1))
SHELLY_IP       = get_setting_value(session, "shelly_ip",       default="192.168.1.100")
PULSE_DURATION  = int(get_setting_value(session, "pulse_duration", default=1))
RELAY_MODE = get_setting_value(session, "relay_mode", default="on").lower()  # "on" or "pulse"

# ----- Initialize serial scanner if available -----
try:
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=SERIAL_BAUDRATE,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=SCAN_TIMEOUT
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
            data = ser.readline().decode("utf-8").strip()
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


def log_scan_event(code_value, result, details=None):
    """Persist a scan attempt to the database."""
    try:
        code_entry = session.query(Code).filter_by(code=code_value).first()
        order_id = code_entry.order_id if code_entry else None

        usage_left_msg = None
        if code_entry:
            usage_left = code_entry.usage_limit - code_entry.current_usage
            if result == "success":
                if usage_left > 0:
                    usage_left_msg = f"Code now has {usage_left} uses left."
                else:
                    usage_left_msg = "Code has now expired."
            elif result == "expired":
                usage_left_msg = "Code has already expired."
            # You can add more result cases here if needed

        if usage_left_msg:
            details = f"{details}; {usage_left_msg}" if details else usage_left_msg

        log_entry = ScanLog(
            code=code_value,
            order_id=order_id,
            timestamp=datetime.utcnow(),
            result=result,
            details=details,
        )
        session.add(log_entry)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.exception("Failed to log scan event: %s", e)


def process_qr_code(scanned_code):
    """Validate code, then trigger Shelly according to mode."""
    try:
        is_valid, code_info = search_table(scanned_code)
        if not is_valid:
            result = "expired" if code_info != "Invalid code" else "invalid"
            logger.warning(
                "Invalid code", extra={"code": scanned_code, "reason": code_info}
            )
            log_scan_event(scanned_code, result, code_info)
            return

        logger.info("Code accepted")
        if RELAY_MODE == "pulse":
            logger.debug("Pulse mode: ON\u2192wait\u2192OFF")
            success = send_shelly_pulse(SHELLY_IP, duration=PULSE_DURATION)
        elif RELAY_MODE == "on":
            logger.debug("ON-only mode")
            success = send_shelly_on(SHELLY_IP)
        else:
            logger.error("Unknown relay mode: %s", RELAY_MODE)
            log_scan_event(scanned_code, "error", f"Unknown relay mode: {RELAY_MODE}")
            return

        if success:
            code_info.current_usage += 1
            if code_info.current_usage >= code_info.usage_limit:
                # Mark code for cleanup after retention period
                try:
                    days = int(
                        get_setting_value(session, "expired_code_cleanup_days", default=30)
                    )
                except (TypeError, ValueError):
                    days = 30
                expire_at = datetime.utcnow()
                if days and days > 0:
                    expire_at = expire_at + timedelta(days=days)
                code_info.expiration_date = expire_at

            session.commit()
            logger.info("Shelly command succeeded", extra={"code": code_info.code})
            log_scan_event(scanned_code, "success")
        else:
            logger.error("Shelly command failed", extra={"code": code_info.code})
            log_scan_event(scanned_code, "fail", "Shelly command failed")
    except Exception as e:
        logger.exception("Error processing QR code")
        log_scan_event(scanned_code, "error", str(e))

def listen_for_scans():
    """Continuously get codes from scanner or input."""
    while True:
        scanned_code = read_qr_code()
        logger.debug("Scanned code received", extra={"code": scanned_code})
        process_qr_code(scanned_code)


if __name__ == "__main__":
    listen_for_scans()
