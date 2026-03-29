# Admin Command Examples

Practical command reference for maintenance, configuration, and manual verification workflows.

## Conventions
- Run commands from repository root.
- Replace placeholders like `<ORDER_ID>` and `<CODE_VALUE>`.
- Default backend URL: `http://127.0.0.1:5000`.
- For admin routes, include both Basic auth and `X-API-KEY`.

## Environment and credentials
```bash
# Generate/read kiosk API key
python backend/scripts/get_api_key.py

# Seed on a fresh DB
python -m backend.setup.seed_settings
python -m backend.setup.seed_machines

# bash/zsh
export API_KEY="<PASTE_API_KEY>"
```

```powershell
# PowerShell
$env:API_KEY = "<PASTE_API_KEY>"
```

## QR code lifecycle
```bash
# Generate code
curl -X POST -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d '{"order_id": "<ORDER_ID>", "usage_limit": 3}' \
  http://127.0.0.1:5000/generate_code

# Validate scan
curl -X POST -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d '{"code": "<CODE_VALUE>"}' \
  http://127.0.0.1:5000/api/scan_code

# Start machine
curl -X POST -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d '{"code": "<CODE_VALUE>", "machine_id": "washer1"}' \
  http://127.0.0.1:5000/api/start_machine

# Button event
curl -X POST -H "X-API-KEY: $API_KEY" -H "Content-Type: application/json" \
  -d '{"button": 0}' \
  http://127.0.0.1:5000/api/i4_event

# UI state
curl -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/api/ui_state
```

## Admin inventory and logs
```bash
# List codes
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/codes

# Latest scan logs
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/scan_logs/last/5

# Usage by order
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/usage/by_order_id/<ORDER_ID>

# Read setting
curl -u admin:<password> -H "X-API-KEY: $API_KEY" http://127.0.0.1:5000/admin/settings/<SETTING_KEY>
```

## Settings updates
```bash
# Update setting value
curl -X PUT -u admin:<password> -H "X-API-KEY: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value": "60"}' \
  http://127.0.0.1:5000/admin/settings/button_select_timeout_sec

# Update CORS origins
curl -X PUT -u admin:<password> -H "X-API-KEY: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"origins": ["http://localhost:3000", "http://192.168.1.50"]}' \
  http://127.0.0.1:5000/admin/settings/cors
```

## Utilities and smoke checks
```bash
# DB inspection helpers
python Testing_Files/view_db.py --table codes --limit 10
python Testing_Files/view_db.py --table settings
python Testing_Files/view_db.py --table scan_logs --limit 20

# Cleanup run (same logic as scheduler)
python -c "from backend.controllers.code_cleanup import cleanup_expired_codes; cleanup_expired_codes()"

# Logger unit test
python -m unittest backend.tests.test_logger

# Tail logs
tail -f backend/logs/app.log
```

## Service control
```bash
python -m backend.app

cd frontend
npm install
npm run dev
```

## Notes
- Re-seed settings/machines after deleting `codes.db`.
- Redistribute API/admin credential changes to kiosks/automation immediately.
- Snapshot DB before destructive production operations.
