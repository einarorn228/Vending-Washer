import logging
import requests
import time
from utils.logger import configure_logger

configure_logger()
logger = logging.getLogger(__name__)

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
            logger.error("Failed to turn ON relay", extra={"ip": ip, "status": on_response.status_code})
            return False

        logger.info("Pulse started", extra={"ip": ip})
        time.sleep(duration)

        # Turn off relay
        off_response = requests.get(off_url, timeout=3)
        if off_response.status_code != 200:
            logger.error("Failed to turn OFF relay", extra={"ip": ip, "status": off_response.status_code})
            return False

        logger.info("Pulse completed successfully", extra={"ip": ip})
        return True

    except Exception:
        logger.exception("Error communicating with Shelly device", extra={"ip": ip})
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
            logger.info("Shelly ON succeeded", extra={"ip": ip})
            return True
        else:
            logger.error("Shelly ON failed", extra={"ip": ip, "status": resp.status_code})
            return False
    except Exception:
        logger.exception("Could not reach Shelly", extra={"ip": ip})
        return False
