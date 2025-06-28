<<<<<<< HEAD
import requests
import time
from utils.shelly_config import shelly_uni_devices, shelly_x_mod1

def start_machine(machine_name, duration):
    """Start the washer or dryer by sending a 12V signal for a set duration."""
    shelly_ip = shelly_uni_devices[machine_name]["ip"]
    relay_url = f"http://{shelly_ip}{shelly_uni_devices[machine_name]['relay_control']}/on"

    try:
        response = requests.get(relay_url)
        if response.status_code == 200:
            print(f"{machine_name} started for {duration} seconds.")
            time.sleep(duration)  # Hold the 12V signal for the specified duration
            stop_machine(machine_name)
        else:
            print(f"Error: Unable to start {machine_name}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error: Could not reach {machine_name}. Details: {e}")

def stop_machine(machine_name):
    """Stop the washer or dryer by turning off the 12V signal."""
    shelly_ip = shelly_uni_devices[machine_name]["ip"]
    relay_url = f"http://{shelly_ip}{shelly_uni_devices[machine_name]['relay_control']}/off"
    try:
        requests.get(relay_url)
        print(f"{machine_name} stopped.")
    except Exception as e:
        print(f"Error: Unable to stop {machine_name}. Details: {e}")

def is_machine_in_use(machine_name):
    """Check if the machine is currently running by reading the Shelly UNI input status."""
    shelly_ip = shelly_uni_devices[machine_name]["ip"]
    status_url = f"http://{shelly_ip}{shelly_uni_devices[machine_name]['input_status']}"

    try:
        response = requests.get(status_url)
        if response.status_code == 200:
            data = response.json()
            return data["inputs"][0]["input"] == 1  # Assume input 1 means the machine is in use
        else:
            print(f"Error: Unable to check status for {machine_name}. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: Could not reach {machine_name}. Details: {e}")
        return False
    
def is_button_pressed(machine_name):
    """Check if a button is pressed using Shelly X MOD1 input."""
    shelly_ip = shelly_x_mod1["ip"]
    button_url = f"http://{shelly_ip}{shelly_x_mod1['button_endpoints'][machine_name]}"

    try:
        response = requests.get(button_url)
        if response.status_code == 200:
            data = response.json()
            return data["inputs"][0]["input"] == 0  # Assume 0 indicates button pressed
        else:
            print(f"Error: Unable to read button for {machine_name}. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error: Could not reach {machine_name} button. Details: {e}")
        return False

def set_led(machine_name, status):
    """Turn LED on or off using Shelly X MOD1 relay output."""
    shelly_ip = shelly_x_mod1["ip"]
    action = "on" if status else "off"
    led_url = f"http://{shelly_ip}{shelly_x_mod1['led_endpoints'][machine_name]}/{action}"

    try:
        response = requests.get(led_url)
        if response.status_code == 200:
            print(f"LED for {machine_name} set to {action}.")
        else:
            print(f"Error: Unable to set LED for {machine_name}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error: Could not reach {machine_name} LED. Details: {e}")

def monitor_buttons():
    """Monitor buttons on Shelly X MOD1 to control Shelly UNI machines and LED indicators."""
    while True:
        for machine_name in shelly_uni_devices:
            # Check machine status
            in_use = is_machine_in_use(machine_name)
            set_led(machine_name, in_use)  # Turn on LED if in use

            # Only process button press if machine is not in use
            if not in_use and is_button_pressed(machine_name):
                start_machine(machine_name, duration=5)  # Start for 5 seconds
                time.sleep(0.5)  # Debounce to avoid multiple presses

            time.sleep(1)  # Delay to prevent excessive requests
=======
def start_machine():
    """Logic to start the washing machine."""
    print("Starting the washing machine...")

def stop_machine():
    """Logic to stop the washing machine."""
    print("Stopping the washing machine...")

def check_machine_status():
    """Logic to check the status of the washing machine."""
    # You could send a request to the washing machine to get its current status
    return "Idle"
>>>>>>> 18712c10707d4f90789e158f42e4eb9880f3771e
