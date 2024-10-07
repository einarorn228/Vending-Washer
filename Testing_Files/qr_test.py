import serial

# Serial setup
ser = serial.Serial(
    port='/dev/ttyACM0',  # Adjust the port as necessary
    baudrate=9600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout= 1
)

while True:
    try:
        # Print the raw data coming from the scanner
        ser_data = ser.readline().decode("utf-8").strip()
        if ser_data:
            print(f"Received data: {ser_data}")
    except Exception as e:
        print(f"Error: {e}")
