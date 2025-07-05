import requests
import time

def send_shelly_pulse(ip, relay=0, duration=1):
    """
    Sends a short pulse to the specified Shelly relay.
    Turns the relay ON, waits for `duration` seconds, then turns it OFF.
    
    Parameters:
        ip (str): IP address of the Shelly device (e.g., "192.168.1.100")
        relay (int): Which relay to toggle (default is 0)
        duration (float): Duration in seconds to keep the relay ON

    Returns:
        bool: True if both ON and OFF requests succeeded, False otherwise
    """

    # Build URLs for Shelly relay control
    on_url = f"http://{ip}/relay/{relay}?turn=on"
    off_url = f"http://{ip}/relay/{relay}?turn=off"

    try:
        # Turn on relay
        on_response = requests.get(on_url, timeout=3)
        if on_response.status_code != 200:
            print(f"[ERROR] Failed to turn ON relay at {ip}. Status: {on_response.status_code}")
            return False

        print(f"[INFO] Pulse started on Shelly at {ip}")
        time.sleep(duration)

        # Turn off relay
        off_response = requests.get(off_url, timeout=3)
        if off_response.status_code != 200:
            print(f"[ERROR] Failed to turn OFF relay at {ip}. Status: {off_response.status_code}")
            return False

        print(f"[INFO] Pulse completed successfully on Shelly at {ip}")
        return True

    except Exception as e:
        print(f"[EXCEPTION] Error communicating with Shelly device at {ip}: {e}")
        return False
    
def send_shelly_on(ip, relay=0):
    """
    Turn a Shelly relay ON via HTTP.
    Returns True if the request succeeds (HTTP 200), False otherwise.
    """
    url = f"http://{ip}/relay/{relay}?turn=on"
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            print(f"[INFO] Shelly ON succeeded at {ip}")
            return True
        else:
            print(f"[ERROR] Shelly ON failed at {ip}. Status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[EXCEPTION] Could not reach Shelly at {ip}: {e}")
        return False