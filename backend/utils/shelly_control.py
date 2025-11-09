import logging
import time

import requests

from backend.metrics import inc, observe_ms

logger = logging.getLogger(__name__)


RETRY_ATTEMPTS = 2


def _perform_request(url, ip, action):
    last_status = None
    last_exception = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        started = time.perf_counter()
        try:
            response = requests.get(url, timeout=3)
            latency_ms = int((time.perf_counter() - started) * 1000)
            observe_ms("shelly_request_ms", latency_ms, device=ip, action=action)
            if response.status_code == 200:
                return True, response.status_code
            last_status = response.status_code
        except Exception as exc:  # pragma: no cover - network errors
            latency_ms = int((time.perf_counter() - started) * 1000)
            observe_ms("shelly_request_ms", latency_ms, device=ip, action=action)
            last_exception = exc
        if attempt < RETRY_ATTEMPTS:
            inc("shelly_retry_total", device=ip, action=action)
    if last_exception:
        raise last_exception
    return False, last_status


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
        overall_start = time.perf_counter()

        on_ok, status = _perform_request(on_url, ip, "turn_on")
        if not on_ok:
            logger.error(
                "Failed to turn ON relay",
                extra={"ip": ip, "status": status},
            )
            return False

        logger.info("Pulse started", extra={"ip": ip})
        time.sleep(duration)

        off_ok, status = _perform_request(off_url, ip, "turn_off")
        if not off_ok:
            logger.error(
                "Failed to turn OFF relay",
                extra={"ip": ip, "status": status},
            )
            return False

        total_ms = int((time.perf_counter() - overall_start) * 1000)
        observe_ms("shelly_rtt_ms", total_ms, device=ip)
        logger.info("Pulse completed successfully", extra={"ip": ip})
        return True

    except Exception:  # pragma: no cover - network errors
        logger.exception("Error communicating with Shelly device", extra={"ip": ip})
        return False


def send_shelly_on(ip, relay=0):
    """
    Turn a Shelly relay ON via HTTP.
    Returns True if the request succeeds (HTTP 200), False otherwise.
    """
    url = f"http://{ip}/relay/{relay}?turn=on"
    try:
        start = time.perf_counter()
        ok, status = _perform_request(url, ip, "turn_on")
        total_ms = int((time.perf_counter() - start) * 1000)
        observe_ms("shelly_rtt_ms", total_ms, device=ip)
        if ok:
            logger.info("Shelly ON succeeded", extra={"ip": ip})
            return True
        logger.error("Shelly ON failed", extra={"ip": ip, "status": status})
        return False
    except Exception:  # pragma: no cover - network errors
        logger.exception("Could not reach Shelly", extra={"ip": ip})
        return False
