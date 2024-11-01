import requests
import RPi.GPIO as GPIO
import time

# Define Shelly UNI IP addresses and button/LED GPIO pins
shelly_devices = {
    "washer_1": {"ip": "192.168.1.101", "button_pin": 17, "led_pin": 23},
    "washer_2": {"ip": "192.168.1.102", "button_pin": 18, "led_pin": 24},
    "dryer_1": {"ip": "192.168.1.103", "button_pin": 27, "led_pin": 25},
    "dryer_2": {"ip": "192.168.1.104", "button_pin": 22, "led_pin": 26}
}

# Setup GPIO mode and pins
GPIO.setmode(GPIO.BCM)
for machine, config in shelly_devices.items():
    GPIO.setup(config["button_pin"], GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Setup button with pull-up resistor
    GPIO.setup(config["led_pin"], GPIO.OUT)  # Setup LED pin as output

def is_machine_in_use(machine_name):
    """Check if the machine is currently in use by reading the Shelly input status."""
    shelly_ip = shelly_devices[machine_name]["ip"]
    url = f"http://{shelly_ip}/status"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Check the input status; assume `data["inputs"][0]["input"]` represents the in-use status
            in_use = data["inputs"][0]["input"] == 1
            return in_use
        else:
            print(f"Error: Unable to check status for {machine_name}. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: Could not reach {machine_name}. Details: {e}")
        return False

def control_machine(machine_name, action):
    """Control the machine by sending an on/off command via REST API."""
    shelly_ip = shelly_devices[machine_name]["ip"]
    url = f"http://{shelly_ip}/relay/0/{action}"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Success: {machine_name} turned {action}.")
        else:
            print(f"Error: Failed to send {action} command to {machine_name}.")
    except Exception as e:
        print(f"Error: Unable to reach {machine_name}. Details: {e}")

def monitor_buttons():
    """Monitor buttons and control machines with LED indicators."""
    while True:
        for machine, config in shelly_devices.items():
            button_pin = config["button_pin"]
            led_pin = config["led_pin"]

            # Check if the machine is currently in use
            if is_machine_in_use(machine):
                GPIO.output(led_pin, GPIO.HIGH)  # Turn on LED to indicate the machine is in use
                print(f"{machine} is currently in use.")
            else:
                GPIO.output(led_pin, GPIO.LOW)   # Turn off LED when the machine is available
                if GPIO.input(button_pin) == GPIO.LOW:  # Button pressed
                    control_machine(machine, "on")
                    time.sleep(0.5)  # Debounce to avoid multiple presses

            time.sleep(1)  # Add a small delay to prevent excessive API requests
