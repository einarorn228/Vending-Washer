# Newland FM3080V2 — USB CDC setup for Vending-Washer

This runbook documents how the **Newland FM3080** family (observed product string `NLS-FM3080V2-20`) must be configured so the Vending-Washer **backend serial scanner** path works on **Linux / Raspberry Pi**.

Code and settings source of truth:
- `backend/controllers/qr_scanner.py`
- `tools/test_scanner.py`
- Settings: `serial_port`, `serial_baudrate`, `scan_timeout` — see [`settings-catalog.md`](../../reference/settings-catalog.md)

## Why USB CDC (not keyboard wedge)

The backend opens a **POSIX serial device** with PySerial (`serial.Serial`). On Linux, **USB CDC ACM** exposes that device as **`/dev/ttyACM0`** (or `ttyACM1`, …).

Other USB personalities for the same hardware **do not** present `ttyACM*`:

| Linux enumeration (examples) | USB product id (hex) | Typical Linux driver stack | Works with `qr_scanner.py`? |
|------------------------------|----------------------|----------------------------|-----------------------------|
| `NLS-FM3080V2-20 USB CDC` | `1eab:0006` | `cdc_acm` → `/dev/ttyACM0` | **Yes** |
| `NLS-FM3080V2-20 USB POS KBW` | `1eab:0022` | `hid-generic` (keyboard) | **No** (no serial port) |
| `NLS-FM3080V2-20 USB HID POS` | `1eab:0010` | `hid-generic` / `hidraw` | **No** (no serial port) |

Use **`lsusb`** and the product string / `idVendor:idProduct` to confirm the active mode after any programming change.

## Official scanner documentation (programming barcodes)

Programming is done by scanning **configuration barcodes** from the manufacturer manual. **Do not guess barcodes** — use the PDF that matches your exact model and revision.

Primary references (download from Newland and keep a copy with the machine file):

- [FM3080 user guide (Newland ID)](https://www.newland-id.com/sites/default/files/documents/2021-02/fm3080_user_guide_v1.0.0.pdf)
- [FM3080 Hind user guide (Newland ID)](https://www.newland-id.com/sites/default/files/documents/2025-05/fm3080_hind_user_guide.pdf)

In the manual, work through the sections that cover:

1. **Enter setup / programming mode** (often a dedicated “enter setup” barcode).
2. **USB interface** (or “USB device type” / “communication interface” — wording varies by manual revision).
3. Select **USB CDC** (sometimes labeled **USB COM**, **virtual COM**, or similar — the manual’s CDC option is the one that pairs with `cdc_acm` on Linux).
4. **Save and exit** / **exit programming** so the setting is stored in the scanner (some devices revert if you skip the final save barcode).

Also check the manual for **serial communication parameters** (baud rate, data bits, parity) and align the database setting **`serial_baudrate`** with the value the scanner uses in CDC mode. The repository default/fallback is **9600**; if your manual specifies a different default after factory reset, match it in settings.

## Linux / Raspberry Pi: drivers

- **No separate “USB CDC driver download” is required on Raspberry Pi OS** for standard CDC ACM devices. The kernel module **`cdc_acm`** binds and creates **`/dev/ttyACM*`**.
- Verify the module is available: `lsmod | grep cdc_acm`
- If the device is in CDC mode and still no `ttyACM*`, the problem is almost always **USB enumeration / power / cable / wrong USB mode**, not a missing proprietary driver (contrast with typical Windows installer packages mentioned in some vendor docs).

## Application settings (must match scanner + host)

These are stored in `codes.db` (`settings` table). See the full catalog: [`settings-catalog.md`](../../reference/settings-catalog.md).

| Setting | Role |
|---------|------|
| `serial_port` | Device path (commonly `/dev/ttyACM0` on Pi when a single CDC scanner is present). |
| `serial_baudrate` | Must match the scanner’s serial baud in CDC mode (often `9600`; confirm in manual). |
| `scan_timeout` | PySerial read timeout (seconds); affects how quickly idle reads return. |

**Restart required:** the scanner module reads these at **import / first serial init**; after changing any of them, **restart the backend** (`python -m backend.app` or your service).

**Unix permissions:** the operator user should be in the **`dialout`** group (or equivalent) so `/dev/ttyACM0` is readable/writable.

## Verification checklist (after programming + cabling)

1. **USB visible to OS**
   ```bash
   lsusb
   ```
   Expect **Newland** with **`1eab:0006`** when CDC mode is active (see table above).

2. **Serial device node**
   ```bash
   ls -l /dev/ttyACM*
   ```
   Expect at least `ttyACM0` when a single CDC device is attached.

3. **Kernel confirmation (optional)**
   ```bash
   dmesg | tail -50
   ```
   Look for `cdc_acm` and `ttyACM0` lines right after plug-in.

4. **Raw serial test (bypasses Flask)**
   ```bash
   cd /path/to/Vending-Washer
   source .venv/bin/activate   # or your venv
   PYTHONPATH=$PWD python tools/test_scanner.py --list-ports
   PYTHONPATH=$PWD python tools/test_scanner.py
   ```
   Scan a code; you should see `RAW` / `DECODED` lines.

5. **Backend integration**
   - Restart backend **after** `ttyACM0` exists (or after changing scanner settings).
   - In `backend/logs/app.log`, expect:
     - `Serial scanner available on /dev/ttyACM0`
     - `Scanner listener thread started on ...`
   - In `backend/logs/events.log`, expect scan-related events when codes are accepted by `ingest_scan`.

## Accepted scan payload shapes (application logic)

The scanner sends a line of text; the backend accepts several shapes (local kiosk codes, UUIDs, etc.). See `backend/controllers/qr_scanner.py` (`_looks_like_scanner_token`). If scans appear in `test_scanner.py` but are **ignored** in the app, check that the decoded string matches those rules.

## Field note: USB replug and shared ports (what fixed our case)

If multiple USB full-speed devices share a path (for example **mouse + scanner** on the same internal hub path), enumeration can occasionally fail until ports are simplified.

**What worked in practice:** power-cycle or **unplug and reconnect** peripherals so the scanner enumerates cleanly, then confirm `lsusb` shows **`1eab:0006`** and `/dev/ttyACM0` appears. After that, **restart the backend** if it had started while the port was missing.

For production kiosks, prefer a **powered USB hub** with a known-good **data** cable for the scanner, and verify enumeration after any wiring change.

## Related runbooks

- [`hardware-and-scanner-troubleshooting.md`](./hardware-and-scanner-troubleshooting.md) — general scanner triage and SQL checks.
- [`runtime-and-process-management.md`](./runtime-and-process-management.md) — keeping processes alive outside SSH sessions.
