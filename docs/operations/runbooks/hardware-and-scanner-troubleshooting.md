# Hardware and Scanner Troubleshooting

Code source of truth:
- scanner: `backend/controllers/qr_scanner.py`
- telemetry: `backend/controllers/telemetry.py`
- relay control: `backend/utils/shelly_control.py`
- machine flow: `backend/controllers/machine_control.py`
- scanner tool: `tools/test_scanner.py`

## Fast triage checklist
1. Confirm backend is running via `python -m backend.app`.
2. Verify API key and `/api/ui_state` response.
3. Check `backend/logs/events.log` and `backend/logs/errors.log`.
4. Run scanner test tool if scanner is suspected.

## Scanner troubleshooting

Newland **FM3080** on Raspberry Pi (USB CDC, `ttyACM0`, programming barcodes, `lsusb` IDs): see **[`scanner-newland-fm3080-cdc.md`](./scanner-newland-fm3080-cdc.md)**.

## Symptom: scanner events never appear
Checks:
```bash
python tools/test_scanner.py
```
Expected healthy output pattern:
- log line about opening serial port
- repeated RAW/DECODED lines when scanner sends bytes

If port open fails, tool logs:
- `Unable to open serial port ...`

Verify scanner settings:
```bash
sqlite3 codes.db "SELECT key,value FROM settings WHERE key IN ('serial_port','serial_baudrate','scan_timeout');"
```

High-risk gotcha:
- scanner serial settings are loaded at import time in `qr_scanner.py`.
- changing scanner settings requires backend restart.

## Symptom: scans ignored
`qr_scanner.py` filters payloads via `_looks_like_scanner_token` (see code). Accepted shapes include, for example:

- 8-character alphanumeric “local kiosk” codes
- UUID strings (with hyphens) and 32-character hex (no hyphens)
- **4–12 digit PIN** strings (Reisa `lookup_auto` path)

If `tools/test_scanner.py` prints a `DECODED` value but the backend ignores it, compare the string against that helper.

### USB CDC: split frames and “late first byte”
Some USB serial scanners deliver one logical barcode as **multiple reads** (for example the UUID body first, then one or two hex characters that belong at the **start** of the string). The backend mitigates this by:

- reading with **`inter_byte_timeout`** and a short **coalesce tail** read (see `INTER_BYTE_TIMEOUT_SEC`, `_read_full_frame` in `qr_scanner.py`),
- **buffering** a UUID-shaped “tail” briefly and **prepending** a following 1–3 hex fragment when it completes a valid UUID,
- **suffix recovery** against the **last successfully ingested UUID** within a TTL when bytes are dropped from the **left** of the whole string (same QR rescanned).

If fragments still appear in `app.log`, increase `scan_timeout` (requires backend restart) and confirm baud rate matches the scanner datasheet.

End-to-end Pi + hardware checklist: [`kiosk-and-e2e-testing.md`](./kiosk-and-e2e-testing.md).

## Serial configuration issues

Common Linux path:
- `/dev/ttyACM0` (default fallback)

Update setting example:
```bash
python - <<'PY'
from backend.models import Session
from backend.models.setting_model import update_setting_value
s = Session()
try:
    update_setting_value(s, 'serial_port', '/dev/ttyUSB0')
finally:
    s.close()
PY
```
Then restart backend.

## Shelly relay troubleshooting

## Symptom: start requested but relay command fails
Checks:
- verify `backend_relay_enabled`
- verify target device IP and relay channel
- check errors log for Shelly request failures

Commands:
```bash
sqlite3 codes.db "SELECT key,value FROM settings WHERE key='backend_relay_enabled';"
sqlite3 codes.db "SELECT id,name,role,ip,relay_channel,input_channel,metric_source FROM devices ORDER BY id;"
```

Relay behavior notes:
- Shelly API generation detection is dynamic (`gen1` vs `gen2`).
- Relay helper retries requests (`RETRY_ATTEMPTS=2`).

## Telemetry offline troubleshooting

## Symptom: machines always unavailable/offline
Checks:
```bash
API_KEY=$(python backend/scripts/get_api_key.py)
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
```

Look for logs:
- `TELEMETRY_READ` warning with status error
- `DEVICE_OFFLINE`

Inspect topology and config:
```bash
sqlite3 codes.db "SELECT id,name,role,ip,metric_source,relay_channel,input_channel FROM devices ORDER BY id;"
sqlite3 codes.db "SELECT machine_id,on_threshold,off_threshold,on_confirm_ms,off_confirm_ms,poll_interval_ms FROM machine_configs ORDER BY machine_id;"
```

## Symptom: machine starts physically but backend never confirms
Likely causes:
- wrong metric source
- thresholds too high/low
- debounce windows misconfigured

Action:
- tune machine config values and re-test start flow.

## Safe operation sequence after hardware changes
1. Backup DB.
2. Update one device/config value.
3. Restart backend.
4. Verify `/api/ui_state` and logs.
5. Perform one controlled scan/start test.

## High-risk operations
- Bulk changing device roles or button indexes without mapping validation.
- Enabling backend relay before verifying each machine-device mapping.

## Unknown / requires verification from code
- No dedicated endpoint exists for live raw telemetry values per machine; diagnostics rely on logs and availability snapshot.
