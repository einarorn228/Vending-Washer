import serial
from models import session, Code
from controllers.machine_control import start_machine

# Serial setup for QR scanner
ser = serial.Serial(
    port='/dev/ttyACM0',  # Adjust the port as necessary
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1  # Set timeout to None to wait for data indefinitely
)

def read_qr_code():
    """Wait for QR code data from the serial port (event-driven)."""
    try:
        ser_data = ser.readline().decode("utf-8").strip()  # Read and decode serial data
        if ser_data:
            print(f"Received QR Code: {ser_data}")
            return ser_data
        return None
    except Exception as e:
        print(f"Error reading from serial port: {e}")
        return None

def search_table(scanned_code):
    """Check if the scanned QR code exists and is valid."""
    code_entry = session.query(Code).filter_by(code=scanned_code).first()

    if code_entry:
        if code_entry.current_usage < code_entry.usage_limit:
            return True, code_entry
        else:
            return False, "Usage limit exceeded"
    else:
        return False, "Invalid code"

def process_qr_code(scanned_code):
    """Process the QR code and control the machine."""
    is_valid, code_info = search_table(scanned_code)

    if is_valid:
        print(f"Code {scanned_code} is valid. Starting the machine...")
        start_machine()  # Call the function to start the machine
        code_info.current_usage += 1  # Increment the current usage
        session.commit()  # Save changes to the database
    else:
        print(f"Invalid code: {code_info}")

def listen_for_scans():
    """Main function to listen for QR code events from the scanner."""
    while True:
        scanned_code = read_qr_code()  # This blocks until data is received
        if scanned_code:
            process_qr_code(scanned_code)

if __name__ == "__main__":
    listen_for_scans()