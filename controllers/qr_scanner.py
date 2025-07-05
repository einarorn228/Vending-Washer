import serial
from models import session
from models.code_model import Code
from models.setting_model import get_setting_value
from utils.shelly_control import send_shelly_pulse, send_shelly_on
from utils.logger import logger

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
    logger.info("Serial scanner available on %s", SERIAL_PORT)
except Exception as e:
    SERIAL_AVAILABLE = False
    logger.warning("Serial scanner not available: %s", e)


def read_qr_code():
    """Reads a QR code—serial if connected, otherwise manual input."""
    if SERIAL_AVAILABLE:
        try:
            data = ser.readline().decode("utf-8").strip()
            if data:
                logger.info("Received QR Code: %s", data)
                return data
        except Exception as e:
            logger.error("Serial read error: %s", e)
    # Fallback to manual typing
    return input("Enter code manually: ")


def search_table(scanned_code):
    code_entry = session.query(Code).filter_by(code=scanned_code).first()
    if code_entry and code_entry.current_usage < code_entry.usage_limit:
        return True, code_entry
    if code_entry:
        return False, "Usage limit exceeded"
    else:
        return False, "Invalid code"


def process_qr_code(scanned_code):
    """Validate code, then trigger Shelly according to mode."""
    is_valid, code_info = search_table(scanned_code)
    if not is_valid:
        logger.warning("Invalid code: %s", code_info)
        return

    logger.info("Code accepted")
    if RELAY_MODE == "pulse":
        logger.info("Pulse mode: ON\u2192wait\u2192OFF")
        success = send_shelly_pulse(SHELLY_IP, duration=PULSE_DURATION)
    elif RELAY_MODE == "on":
        logger.info("ON-only mode")
        success = send_shelly_on(SHELLY_IP)
    else:
        logger.error("Unknown relay mode: %s", RELAY_MODE)
        return

    if success:
        code_info.current_usage += 1
        session.commit()
        logger.info("Shelly command succeeded. Code marked as used.")
    else:
        logger.error("Shelly command failed. Code not marked.")

def listen_for_scans():
    """Continuously get codes from scanner or input."""
    while True:
        scanned_code = read_qr_code()
        process_qr_code(scanned_code)


if __name__ == "__main__":
    listen_for_scans()
