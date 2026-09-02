import logging
import threading
import time
import uuid
from typing import Optional

import serial

from backend.models import session
from backend.models.setting_model import get_setting_value
from backend.services.start_orchestrator import ingest_scan

logger = logging.getLogger(__name__)


SERIAL_PORT = "/dev/ttyACM0"
SERIAL_BAUDRATE = 9600
SCAN_TIMEOUT = 3.0
EXPECTED_CODE_LENGTH = 8
# After the first byte, return from read() when this many seconds pass with no new byte (full barcode frame).
# USB CDC skannar geta haft >200 ms bil milli bæta undir álagi; of stutt gildi sker UUID í tvennt.
INTER_BYTE_TIMEOUT_SEC = 0.55
READ_CHUNK_MAX = 512
# Eftir að fyrsti pakki er kominn, bíða stutt og drepa inn restina (sama skönnun skipt yfir nokkra USB-pakka).
COALESCE_TRAIL_QUIET_SEC = 0.06
COALESCE_MAX_EXTRA_SEC = 0.25

ser = None
SERIAL_AVAILABLE = False
_serial_init_lock = threading.Lock()
_serial_initialized = False

# USB CDC getur týnt fyrstu 1–8 bætum í næstu lesingu. Ef sami QR kemur strax aftur sem „skertur“ strengur,
# er hægt að endurvinna úr síðasta gilda UUID (einkvæmt, ólíkt því að giska aðeins á fyrsta hóp).
_RECENT_FULL_UUID: Optional[str] = None
_RECENT_FULL_UUID_MONO: float = 0.0
_RECENT_UUID_TTL_SEC = 45.0
_MAX_LEADING_BYTES_DROP = 8

# Stundum kemur fyrsti hluti UUID (án fyrstu 1–3 hex) í einum pakka og vantandi forstafur (t.d. "f") í næsta.
_UUID_TAIL_PENDING: Optional[str] = None
_UUID_TAIL_PENDING_MONO: float = 0.0
_LEADING_HEX_ORPHAN: Optional[str] = None
_LEADING_HEX_ORPHAN_MONO: float = 0.0
_FRAGMENT_BUFFER_TTL_SEC = 0.45


def _clear_fragment_buffers() -> None:
    global _UUID_TAIL_PENDING, _LEADING_HEX_ORPHAN
    _UUID_TAIL_PENDING = None
    _LEADING_HEX_ORPHAN = None


def _hex_only(s: str) -> bool:
    return bool(s) and all(c in "0123456789abcdefABCDEF" for c in s)


def _small_hex_prefix_fragment(s: str) -> bool:
    """1–3 hex án bandstriks — getur verið of seinn forstafur fyrir vantandi UUID-hala."""

    t = (s or "").strip()
    return 1 <= len(t) <= 3 and "-" not in t and _hex_only(t)


def _tiny_leading_orphan(s: str) -> bool:
    """1–2 hex — forstafur sem bíður næstu línu með bandstriki (minna árekstur við PIN)."""

    t = (s or "").strip()
    return 1 <= len(t) <= 2 and "-" not in t and _hex_only(t)


def _is_uuid_tail_pending_shape(s: str) -> bool:
    """Líkt UUID en ógilt (t.d. fyrsti hópur 4–7 hex)."""

    t = (s or "").strip()
    try:
        uuid.UUID(t)
        return False
    except ValueError:
        pass
    parts = t.split("-")
    if len(parts) != 5:
        return False
    p0, p1, p2, p3, p4 = parts
    if any(len(x) != 4 for x in (p1, p2, p3)) or len(p4) != 12:
        return False
    if not (4 <= len(p0) <= 7):
        return False
    return all(_hex_only(x) for x in parts)


def _flush_stale_fragment_buffers() -> None:
    global _UUID_TAIL_PENDING, _LEADING_HEX_ORPHAN, _UUID_TAIL_PENDING_MONO, _LEADING_HEX_ORPHAN_MONO

    now = time.monotonic()
    if _UUID_TAIL_PENDING and now - _UUID_TAIL_PENDING_MONO > _FRAGMENT_BUFFER_TTL_SEC:
        logger.debug("Dropping stale uuid-tail fragment buffer: %r", _UUID_TAIL_PENDING[:80])
        _UUID_TAIL_PENDING = None
    if _LEADING_HEX_ORPHAN and now - _LEADING_HEX_ORPHAN_MONO > _FRAGMENT_BUFFER_TTL_SEC:
        logger.debug("Dropping stale leading hex orphan: %r", _LEADING_HEX_ORPHAN)
        _LEADING_HEX_ORPHAN = None


def _prepare_decoded_line(decoded: str) -> Optional[str]:
    """Sameina USB-brot; skila streng til _handle eða None ef línan vareingöngu bufferað."""

    global _UUID_TAIL_PENDING, _UUID_TAIL_PENDING_MONO, _LEADING_HEX_ORPHAN, _LEADING_HEX_ORPHAN_MONO

    d = (decoded or "").strip()
    if not d:
        return None

    now = time.monotonic()
    _flush_stale_fragment_buffers()

    # Gild UUID / local / PIN — hreinsa bið og halda áfram
    if _looks_like_scanner_token(d):
        _clear_fragment_buffers()
        return d

    # Forstafur (1–2) sem á að setja fyrir næstu línu með bandstriki
    if _LEADING_HEX_ORPHAN and now - _LEADING_HEX_ORPHAN_MONO <= _FRAGMENT_BUFFER_TTL_SEC and "-" in d:
        merged = _LEADING_HEX_ORPHAN + d
        _LEADING_HEX_ORPHAN = None
        logger.debug("Merged leading hex orphan + scan line")
        d = merged
        if _looks_like_scanner_token(d):
            _clear_fragment_buffers()
            return d

    # Seinn 1–3 stafa hex forstafur + geymdur UUID-hali
    if (
        _UUID_TAIL_PENDING
        and now - _UUID_TAIL_PENDING_MONO <= _FRAGMENT_BUFFER_TTL_SEC
        and _small_hex_prefix_fragment(d)
    ):
        merged = d + _UUID_TAIL_PENDING
        _UUID_TAIL_PENDING = None
        logger.info("Merged split USB UUID (prefix fragment + tail): %s", merged[:80])
        return merged

    # Nýr ógildur en UUID-líkur hali — geyma (bíða eftir mögulegum forstaf í næsta pakka)
    if _is_uuid_tail_pending_shape(d):
        _UUID_TAIL_PENDING = d
        _UUID_TAIL_PENDING_MONO = now
        logger.debug("Buffering uuid-shaped tail for late leading hex fragment: %r", d[:80])
        return None

    # Einangraður litill hex — geyma sem mögulegan forstaf
    if _tiny_leading_orphan(d) and not _UUID_TAIL_PENDING:
        _LEADING_HEX_ORPHAN = d
        _LEADING_HEX_ORPHAN_MONO = now
        logger.debug("Buffering possible leading hex orphan: %r", d)
        return None

    return d


def _set_recent_successful_uuid(identifier: str) -> None:
    global _RECENT_FULL_UUID, _RECENT_FULL_UUID_MONO
    try:
        _RECENT_FULL_UUID = str(uuid.UUID(identifier.strip()))
        _RECENT_FULL_UUID_MONO = time.monotonic()
    except ValueError:
        pass


def _recover_from_recent_leading_byte_loss(scan: str) -> Optional[str]:
    """Ef scan er sama og síðasta gilda UUID án fyrstu k bæta (1..8), skila fullri UUID."""

    scan = (scan or "").strip()
    if not scan:
        return None
    try:
        uuid.UUID(scan)
        return None
    except ValueError:
        pass

    global _RECENT_FULL_UUID, _RECENT_FULL_UUID_MONO
    full = _RECENT_FULL_UUID
    if not full or time.monotonic() - _RECENT_FULL_UUID_MONO > _RECENT_UUID_TTL_SEC:
        return None
    if scan == full or len(scan) >= len(full):
        return None
    scan_cmp = scan.casefold()
    for k in range(1, min(_MAX_LEADING_BYTES_DROP + 1, len(full))):
        if full[k:].casefold() == scan_cmp:
            _RECENT_FULL_UUID_MONO = time.monotonic()
            return full
    return None


def _looks_like_scanner_token(value: str) -> bool:
    """True for local kiosk codes, Reisa UUIDs, 32-char hex UUIDs, or short Reisa PIN (digits)."""

    v = (value or "").strip()
    if not v:
        return False
    try:
        uuid.UUID(v)
        return True
    except ValueError:
        pass
    if len(v) == 32 and all(c in "0123456789abcdefABCDEF" for c in v):
        return True
    if len(v) == EXPECTED_CODE_LENGTH and v.isalnum():
        return True
    # Reisa lookup_auto accepts PIN (digits); typical lengths 4–12.
    if v.isdigit() and 4 <= len(v) <= 12:
        return True
    return False


def _read_scanner_settings() -> tuple[str, int, float]:
    port = get_setting_value(session, "serial_port", default="/dev/ttyACM0")
    baud = get_setting_value(session, "serial_baudrate", default=9600)
    timeout = get_setting_value(session, "scan_timeout", default=3)
    # scan_timeout is a float setting (see dev_admin SETTING_SCHEMA); a fractional
    # value must not break scanner startup, so coerce leniently.
    try:
        timeout_value = float(timeout)
    except (TypeError, ValueError):
        timeout_value = 3.0
    try:
        baud_value = int(baud)
    except (TypeError, ValueError):
        baud_value = 9600
    return str(port), baud_value, timeout_value


def _ensure_serial_ready() -> bool:
    global ser, SERIAL_AVAILABLE, SERIAL_PORT, SERIAL_BAUDRATE, SCAN_TIMEOUT, _serial_initialized

    with _serial_init_lock:
        if _serial_initialized:
            return SERIAL_AVAILABLE and ser is not None

        SERIAL_PORT, SERIAL_BAUDRATE, SCAN_TIMEOUT = _read_scanner_settings()
        try:
            # timeout: wait for first byte. inter_byte_timeout: end read after a quiet gap (barcode frame), avoids
            # readline() splitting one scan across multiple "lines" when LF/CR is slow or missing.
            ser = serial.Serial(
                port=SERIAL_PORT,
                baudrate=SERIAL_BAUDRATE,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=float(SCAN_TIMEOUT),
                inter_byte_timeout=INTER_BYTE_TIMEOUT_SEC,
            )
            ser.reset_input_buffer()
            SERIAL_AVAILABLE = True
            logger.info("Serial scanner available on %s", SERIAL_PORT)
        except Exception as exc:  # pragma: no cover - depends on hardware
            logger.warning("Serial scanner not available: %s", exc)
            SERIAL_AVAILABLE = False
            ser = None
        _serial_initialized = True
        return SERIAL_AVAILABLE and ser is not None


def _valid_scan_string(value: str) -> bool:
    """Return True if the scanned string may be a local code or external entitlement id."""

    if _looks_like_scanner_token(value):
        return True
    v = (value or "").strip()
    logger.debug(
        "Ignoring scan %r: expected %d-char alphanumeric local code or UUID",
        v,
        EXPECTED_CODE_LENGTH,
    )
    return False


def _read_full_frame(ser_port) -> bytes:
    """Read one logical scan: first pyserial read() plus trailing bytes that arrive shortly after (coalesce)."""

    raw = ser_port.read(READ_CHUNK_MAX)
    if not raw:
        return b""
    quiet_deadline = time.monotonic() + COALESCE_TRAIL_QUIET_SEC
    hard_deadline = time.monotonic() + COALESCE_MAX_EXTRA_SEC
    while time.monotonic() < hard_deadline:
        pending = int(getattr(ser_port, "in_waiting", 0) or 0)
        if pending > 0:
            raw += ser_port.read(min(pending, READ_CHUNK_MAX))
            quiet_deadline = time.monotonic() + COALESCE_TRAIL_QUIET_SEC
            continue
        if time.monotonic() >= quiet_deadline:
            break
        time.sleep(0.002)
    return raw


def _split_scan_segments(raw: bytes) -> list[bytes]:
    """Split one USB-serial read into one or more scans (CR/LF separated)."""

    if not raw:
        return []
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    chunks = [c.strip(b" \t\x00") for c in normalized.split(b"\n") if c.strip(b" \t\x00")]
    if chunks:
        return chunks
    single = raw.strip(b" \t\r\n\x00")
    return [single] if single else []


def _handle_scanned_value(decoded: str) -> None:
    """Invoke the shared scan handler with logging around outcomes."""

    recovered = _recover_from_recent_leading_byte_loss(decoded)
    use = recovered if recovered else decoded

    if not _valid_scan_string(use):
        if decoded and len(decoded) >= 4:
            logger.info(
                "Scanner line ignored (expected 8-char local code, UUID, or 4-12 digit PIN): %r",
                decoded[:128],
            )
        elif decoded:
            logger.debug("Scanner noise ignored (short fragment): %r", decoded[:32])
        return

    if recovered:
        logger.info("Recovered USB-truncated UUID scan %r -> %s", decoded[:128], use)

    try:
        outcome = ingest_scan(use, source="scanner")
        if outcome.success:
            _set_recent_successful_uuid(use)
            _clear_fragment_buffers()
            logger.info("Accepted scan: %s", use)
        else:
            logger.warning("Scan rejected: %s (reason=%s)", use, outcome.message)
    except Exception as exc:  # pragma: no cover - defensive for runtime issues
        logger.exception("Error processing QR code: %s", exc)


def scanner_loop() -> None:
    """Continuously read from the serial scanner and process scans."""

    if not SERIAL_AVAILABLE:
        logger.warning("Scanner loop not started: serial unavailable")
        return

    logger.info("Starting scanner loop on %s", SERIAL_PORT)

    while True:
        try:
            raw = _read_full_frame(ser)
        except Exception as exc:  # pragma: no cover - depends on hardware
            logger.error("Error reading from scanner: %s", exc)
            continue

        if not raw:
            continue

        logger.debug("Raw scan bytes: %r", raw)

        for segment in _split_scan_segments(raw):
            decoded = segment.decode("utf-8", errors="ignore").strip()
            if not decoded:
                if segment:
                    logger.info(
                        "Scanner segment %d byte(s) empty after decode/strip: %r",
                        len(segment),
                        segment[:64],
                    )
                continue
            logger.debug("Decoded scan string: '%s'", decoded)
            to_handle = _prepare_decoded_line(decoded)
            if to_handle is not None:
                _handle_scanned_value(to_handle)


_scanner_thread: Optional[threading.Thread] = None
_thread_lock = threading.Lock()


def start_scanner_listener() -> None:
    """Start the scanner loop in a background daemon thread once."""

    global _scanner_thread

    if not _ensure_serial_ready():
        logger.warning("Scanner listener not started because serial is unavailable")
        return

    with _thread_lock:
        if _scanner_thread and _scanner_thread.is_alive():
            logger.debug("Scanner listener already running")
            return

        _scanner_thread = threading.Thread(
            target=scanner_loop,
            name="qr-scanner-listener",
            daemon=True,
        )
        _scanner_thread.start()
        logger.info("Scanner listener thread started on %s", SERIAL_PORT)


def listen_for_scans() -> None:
    """Backward-compatible entrypoint to run the scanner loop in the foreground."""

    _ensure_serial_ready()
    scanner_loop()


if __name__ == "__main__":
    listen_for_scans()
