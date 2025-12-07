import logging
import time
from typing import Dict, Tuple

import requests

from backend.metrics import inc, observe_ms

logger = logging.getLogger(__name__)


RETRY_ATTEMPTS = 2
API_GEN_CACHE: Dict[str, str] = {}


def detect_api_gen(ip: str) -> str:
    """Detect whether a Shelly device uses the Gen1 or Gen2 API."""

    cached = API_GEN_CACHE.get(ip)
    if cached:
        return cached

    try:
        response = requests.get(
            f"http://{ip}/rpc/Shelly.GetDeviceInfo", timeout=2  # type: ignore[arg-type]
        )
        if response.status_code == 200:
            try:
                response.json()
                API_GEN_CACHE[ip] = "gen2"
                return "gen2"
            except ValueError:
                logger.debug("Shelly GetDeviceInfo non-JSON", extra={"ip": ip})
    except Exception:
        logger.debug("Shelly Gen2 probe failed", exc_info=True, extra={"ip": ip})

    API_GEN_CACHE[ip] = "gen1"
    return "gen1"


def _perform_request(url: str, ip: str, action: str) -> Tuple[bool, int]:
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
    return False, last_status or 0


def _relay_value(relay):
    try:
        return int(relay)
    except (TypeError, ValueError):
        return 0


def _device_ip_and_relay(device, relay_override=None) -> Tuple[str, int]:
    ip = getattr(device, "ip", None) or device
    relay = relay_override if relay_override is not None else getattr(device, "relay_channel", 0)
    return ip, _relay_value(relay)


def _build_switch_url(api_gen: str, ip: str, relay: int, action: str) -> str:
    if api_gen == "gen2":
        if action == "toggle":
            return f"http://{ip}/rpc/Switch.Toggle?id={relay}"
        on_value = "true" if action == "on" else "false"
        return f"http://{ip}/rpc/Switch.Set?id={relay}&on={on_value}"

    turn = "toggle" if action == "toggle" else action
    return f"http://{ip}/relay/{relay}?turn={turn}"


def _switch_request(ip: str, relay: int, action: str) -> bool:
    api_gen = detect_api_gen(ip)
    url = _build_switch_url(api_gen, ip, relay, action)
    ok, status = _perform_request(url, ip, f"switch_{action}")
    if not ok:
        logger.error(
            "Shelly switch action failed",
            extra={"ip": ip, "relay": relay, "action": action, "status": status},
        )
    return ok


def _record_rtt(ip: str, started: float, action: str) -> None:
    total_ms = int((time.perf_counter() - started) * 1000)
    observe_ms("shelly_rtt_ms", total_ms, device=ip, action=action)


def shelly_switch_on(device, relay_override=None) -> bool:
    ip, relay = _device_ip_and_relay(device, relay_override)
    started = time.perf_counter()
    try:
        ok = _switch_request(ip, relay, "on")
        _record_rtt(ip, started, "turn_on")
        if ok:
            logger.info("Shelly ON succeeded", extra={"ip": ip, "relay": relay})
        return ok
    except Exception:  # pragma: no cover - network errors
        logger.exception("Could not reach Shelly", extra={"ip": ip, "relay": relay})
        return False


def shelly_switch_off(device, relay_override=None) -> bool:
    ip, relay = _device_ip_and_relay(device, relay_override)
    started = time.perf_counter()
    try:
        ok = _switch_request(ip, relay, "off")
        _record_rtt(ip, started, "turn_off")
        if ok:
            logger.info("Shelly OFF succeeded", extra={"ip": ip, "relay": relay})
        return ok
    except Exception:  # pragma: no cover - network errors
        logger.exception("Could not reach Shelly", extra={"ip": ip, "relay": relay})
        return False


def shelly_switch_toggle(device, relay_override=None) -> bool:
    ip, relay = _device_ip_and_relay(device, relay_override)
    started = time.perf_counter()
    try:
        ok = _switch_request(ip, relay, "toggle")
        _record_rtt(ip, started, "toggle")
        if ok:
            logger.info("Shelly TOGGLE succeeded", extra={"ip": ip, "relay": relay})
        return ok
    except Exception:  # pragma: no cover - network errors
        logger.exception("Could not reach Shelly", extra={"ip": ip, "relay": relay})
        return False


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

    try:
        overall_start = time.perf_counter()

        if not shelly_switch_on(ip, relay_override=relay):
            logger.error("Failed to turn ON relay", extra={"ip": ip, "relay": relay})
            return False

        logger.info("Pulse started", extra={"ip": ip, "relay": relay})
        time.sleep(duration)

        if not shelly_switch_off(ip, relay_override=relay):
            logger.error("Failed to turn OFF relay", extra={"ip": ip, "relay": relay})
            return False

        _record_rtt(ip, overall_start, "pulse")
        logger.info("Pulse completed successfully", extra={"ip": ip, "relay": relay})
        return True

    except Exception:  # pragma: no cover - network errors
        logger.exception("Error communicating with Shelly device", extra={"ip": ip})
        return False


def send_shelly_on(ip, relay=0):
    """
    Backwards-compatible wrapper to turn a Shelly relay ON via the abstracted helper.
    """

    return shelly_switch_on(ip, relay_override=relay)


def send_shelly_off(ip, relay=0):
    """Backwards-compatible wrapper to turn a Shelly relay OFF via the abstracted helper."""

    return shelly_switch_off(ip, relay_override=relay)
