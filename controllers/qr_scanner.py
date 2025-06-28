#import serial
from models import session
from models.code_model import Code
from utils.shelly_control import send_shelly_pulse

"""
def process_qr_code(scanned_code):
    code_entry = session.query(Code).filter_by(code=scanned_code).first()

    if code_entry:
        if code_entry.current_usage < code_entry.usage_limit:
            print(f"[VALID] Starting machine for code {scanned_code}")
            code_entry.current_usage += 1
            session.commit()
        else:
            print("[INVALID] Code already used.")
    else:
        print("[INVALID] Code not found.")

def listen_for_scans():
    while True:
        scanned_code = input("Scan a code (or type manually): ")
        process_qr_code(scanned_code)
"""

"""
# Serial setup for QR scanner
ser = serial.Serial(
    port='/dev/ttyACM0',  # Change if your device uses a different port
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1  # Timeout in seconds
)
"""
# Shelly configuration
SHELLY_IP = "192.168.10.229"  # Change this to match your Shelly device IP
PULSE_DURATION = 1  # seconds

def read_qr_code():
    """Reads a single line from the QR scanner."""
    try:
        ser_data = ser.readline().decode("utf-8").strip()
        if ser_data:
            print(f"[SCAN] Received QR Code: {ser_data}")
            return ser_data
    except Exception as e:
        print(f"[ERROR] Reading from serial: {e}")
    return None

def search_table(scanned_code):
    """Looks up the scanned code in the database."""
    code_entry = session.query(Code).filter_by(code=scanned_code).first()
    if code_entry:
        if code_entry.current_usage < code_entry.usage_limit:
            return True, code_entry
        else:
            return False, "Usage limit exceeded"
    return False, "Invalid code"

def process_qr_code(scanned_code):
    """Handles a scanned QR code by validating and triggering machine pulse."""
    is_valid, code_info = search_table(scanned_code)

    if is_valid:
        print(f"[VALID] Code accepted. Sending pulse to Shelly...")
        pulse_success = send_shelly_pulse(SHELLY_IP, duration=PULSE_DURATION)
        if pulse_success:
            code_info.current_usage += 1
            session.commit()
            print(f"[OK] Pulse succeeded. Code marked as used.")
        else:
            print(f"[FAIL] Pulse failed. Code was not marked.")
    else:
        print(f"[INVALID] {code_info}")

def listen_for_scans():
    while True:
        scanned_code = input("Scan a code (or type manually): ")
        process_qr_code(scanned_code)
"""
def listen_for_scans():
    ""continuously waits for QR scans and processes them.""
    while True:
        scanned_code = read_qr_code()
        if scanned_code:
            process_qr_code(scanned_code)
"""

if __name__ == "__main__":
    listen_for_scans()
