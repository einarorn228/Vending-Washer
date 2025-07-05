import serial
from models import session
from models.code_model import Code
from models.setting_model import get_setting_value
from utils.shelly_control import send_shelly_pulse, send_shelly_on

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
    print(f"[INFO] Serial scanner available on {SERIAL_PORT}")
except Exception as e:
    SERIAL_AVAILABLE = False
    print(f"[WARNING] Serial scanner not available: {e}")


def read_qr_code():
    """Reads a QR code—serial if connected, otherwise manual input."""
    if SERIAL_AVAILABLE:
        try:
            data = ser.readline().decode("utf-8").strip()
            if data:
                print(f"[SCAN] Received QR Code: {data}")
                return data
        except Exception as e:
            print(f"[ERROR] Serial read error: {e}")
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
        print(f"[INVALID] {code_info}")
        return

    print(f"[VALID] Code accepted.")
    if RELAY_MODE == "pulse":
        print("[MODE] Pulse mode: ON→wait→OFF")
        success = send_shelly_pulse(SHELLY_IP, duration=PULSE_DURATION)
    elif RELAY_MODE == "on":
        print("[MODE] ON-only mode")
        success = send_shelly_on(SHELLY_IP)
    else:
        print(f"[ERROR] Unknown relay mode: {RELAY_MODE}")
        return

    if success:
        code_info.current_usage += 1
        session.commit()
        print("[OK] Shelly command succeeded. Code marked as used.")
    else:
        print("[FAIL] Shelly command failed. Code not marked.")

def listen_for_scans():
    """Continuously get codes from scanner or input."""
    while True:
        scanned_code = read_qr_code()
        process_qr_code(scanned_code)


if __name__ == "__main__":
    listen_for_scans()