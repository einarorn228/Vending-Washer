# Vending Washer

This project powers a simple QR-code based vending washer prototype.

## Project Structure

```
backend/   - Flask API and machine logic
frontend/  - React touchscreen UI
```

The backend exposes API endpoints that the touchscreen UI polls.

## Build and Run

### Backend

```bash
cd backend
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
python setup/seed_settings.py  # create API key and default settings
python app.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on port 3000 by default and communicates with the backend on port 5000.

## Display-only UI

The React frontend does **not** accept any input. It simply polls
`GET /api/ui_state` every second and renders the state returned by the backend.
External triggers such as barcode scanners or physical buttons should call
`POST /api/scan_code` and `POST /api/start_machine` directly to update the
backend. The screen then updates automatically.

### UI API Endpoints

- `POST /api/scan_code` – validate a code (used by external devices)
- `POST /api/start_machine` – start a machine using a valid code
- `GET /api/ui_state` – poll current UI state (used by the frontend)

All requests require the `X-API-KEY` header matching the value stored in the database.

## Kiosk Mode

On Linux you can launch the frontend fullscreen with:

```bash
npm run dev -- --open
```

Press F11 to toggle kiosk mode in most browsers. On Windows use Chrome's `--kiosk` flag when starting the browser.

## Logging

Logging is configured centrally in `utils/logger.py`. A rotating log file is stored in `logs/app.log` and messages are also printed to the console.

### Log Level

The log level defaults to `INFO` but can be adjusted by setting the environment variable `LOG_LEVEL` before running the application:

```bash
export LOG_LEVEL=DEBUG
```

If a `log_level` entry exists in the `settings` table, it will be used when the environment variable is not set.

### Log Directory

The `setup/setup_logs.py` script creates the `logs/` directory with permissions suitable for multi-user deployments (755 for the folder and 644 for the log file). Run it once before starting the app:

```bash
python setup/setup_logs.py
```

### Advanced

Logs rotate after reaching 5MB with three backups kept. For production deployments you might extend `utils/logger.py` to forward logs to external systems (e.g., email or Slack).

---

## Viewing the Database

You can use the script `Testing_Files/view_db.py` to view the contents of your database tables from the command line.

### Usage

```bash
python Testing_Files/view_db.py [--table TABLE] [--limit N] [--code CODE] [--order_id ORDER_ID] [--key KEY]
```

- `--table`  
  Which table to view. Options are:  
  - `codes` (default)  
  - `settings`  
  - `scan_logs`  

- `--limit`  
  How many rows to display (default: all rows).

- `--code`  
  Filter by code value (for `codes` and `scan_logs` tables).

- `--order_id`  
  Filter by order ID (for `codes` and `scan_logs` tables).

- `--key`  
  Filter by key (for `settings` table).

### Examples

- **View all codes:**  
  ```bash
  python Testing_Files/view_db.py
  ```

- **View first 5 codes:**  
  ```bash
  python Testing_Files/view_db.py --limit 5
  ```

- **View all settings:**  
  ```bash
  python Testing_Files/view_db.py --table settings
  ```

- **View a specific setting by key:**  
  ```bash
  python Testing_Files/view_db.py --table settings --key log_level
  ```

- **View all scan logs:**  
  ```bash
  python Testing_Files/view_db.py --table scan_logs
  ```

- **View the 10 most recent scan logs:**  
  ```bash
  python Testing_Files/view_db.py --table scan_logs --limit 10
  ```

- **View all codes with a specific order ID:**  
  ```bash
  python Testing_Files/view_db.py --table codes --order_id 12345
  ```

- **View all scan logs for a specific code:**  
  ```bash
  python Testing_Files/view_db.py --table scan_logs --code ABC123
  ```

- **View all scan logs for a specific order ID:**  
  ```bash
  python Testing_Files/view_db.py --table scan_logs --order_id 12345
  ```

---

## Admin & Debug API Endpoints

The Flask server provides several admin/debug endpoints for monitoring and managing codes and usage.  
**Note:** These endpoints are for admin/debug use only and should be protected before use in production.

### List of Admin Endpoints

- **Get all codes:**  
  ```
  GET /admin/codes
  ```
  Returns all QR codes in the database.

- **Get last N created codes:**  
  ```
  GET /admin/codes/last/<count>
  ```
  Returns the last `<count>` created codes.

- **Get all codes by order ID:**  
  ```
  GET /admin/codes/by_order_id/<order_id>
  ```
  Returns all codes associated with the given order ID.

- **Get info about a specific code:**  
  ```
  GET /admin/codes/<code>
  ```
  Returns info about a specific code.

- **Delete a code by code:**  
  ```
  DELETE /admin/codes/<code>
  ```
  Deletes a specific code.

- **Delete all codes for an order ID:**  
  ```
  DELETE /admin/codes/by_order_id/<order_id>
  ```
  Deletes all codes associated with the given order ID.

- **Update a setting:**  
  ```
  PUT /admin/settings/<key>
  ```
  Updates a setting value.  
  Example body:
  ```json
  { "value": "new_value" }
  ```

- **Get all scan log entries for an order ID:**  
  ```
  GET /admin/usage/by_order_id/<order_id>
  ```
  Returns all scan log entries for the given order ID, including timestamp, result, and details.

- **Get all scan log entries for a code:**  
  ```
  GET /admin/usage/by_code/<code>
  ```
  Returns all scan log entries for the given code, including timestamp, result, and details.

- **Get the last N scan log entries:**
  ```
  GET /admin/scan_logs/last/<count>
  ```
  Returns the last `<count>` scan log entries.

- **Update allowed CORS origins:**
  ```
  PUT /admin/settings/cors
  ```
  Update the comma-separated list of allowed origins.

- **Get or update any setting:**
  ```
  GET /admin/settings/<key>
  PUT /admin/settings/<key>
  ```
  Retrieve or change a setting value.

### Example Usage with curl

- Get all codes:
  ```bash
  curl http://127.0.0.1:5000/admin/codes
  ```

- Get last 10 codes:
  ```bash
  curl http://127.0.0.1:5000/admin/codes/last/10
  ```

- Get all codes for order ID 12345:
  ```bash
  curl http://127.0.0.1:5000/admin/codes/by_order_id/12345
  ```

- Get info about code ABC123:
  ```bash
  curl http://127.0.0.1:5000/admin/codes/ABC123
  ```

- Delete code ABC123:
  ```bash
  curl -X DELETE http://127.0.0.1:5000/admin/codes/ABC123
  ```

- Delete all codes for order ID 12345:
  ```bash
  curl -X DELETE http://127.0.0.1:5000/admin/codes/by_order_id/12345
  ```

- Update a setting (e.g. set cleanup days to 7):
  ```bash
  curl -X PUT http://127.0.0.1:5000/admin/settings/expired_code_cleanup_days \
    -H "Content-Type: application/json" \
    -d '{"value": "7"}'
  ```

- Get all scan logs for order ID 12345:
  ```bash
  curl http://127.0.0.1:5000/admin/usage/by_order_id/12345
  ```

- Get all scan logs for code ABC123:
  ```bash
  curl http://127.0.0.1:5000/admin/usage/by_code/ABC123
  ```

- Get the last 5 scan logs:
  ```bash
  curl http://127.0.0.1:5000/admin/scan_logs/last/5
  ```

---
**Remember:**
These endpoints are powerful for debugging and admin tasks.
**Always add authentication before exposing them in production!**

## API Key and Admin Operations

The server requires an API key for non-admin endpoints. Run the seeding script
once to generate the key if it does not exist:

```bash
python setup/seed_settings.py
```

Retrieve the key locally with:

```bash
python scripts/get_api_key.py
```

**Remember:**  
These endpoints are powerful for debugging and admin tasks.  
**Always add authentication before exposing them in production!**

---

## Code Expiration and Cleanup

Generated QR codes may automatically expire based on values in the `settings` table.

- `code_expiration_days` – Number of days after creation that an unused code will expire. Set to `0` to disable.
- `expired_code_cleanup_days` – When a code has reached its usage limit it is marked for deletion this many days later. Set to `0` to remove immediately.

If a code's `expiration_date` is `None`, it will never expire while unused.

Expired codes are removed by `controllers.code_cleanup.cleanup_expired_codes`. `app.py` starts a background thread that runs this cleanup every 24 hours.

Example lifecycle:
1. `/generate_code` creates a code with an expiration date in UTC if `code_expiration_days` > 0.
2. When the code is scanned and reaches its usage limit, a new expiration date is set according to `expired_code_cleanup_days`.
3. The cleanup job deletes codes whose `expiration_date` has

Include this value in the `X-API-KEY` header when calling general API
endpoints.

Allowed CORS origins are stored in the `cors_allowed_origins` setting as a
comma-separated list. Admins can update it with:

```bash
curl -X PUT -u admin:yourpassword \
  -H "Content-Type: application/json" \
  -d '{"origins": ["http://localhost"]}' \
  http://127.0.0.1:5000/admin/settings/cors
```

### Rotating the API key or changing the admin password

Use the generic settings endpoint to modify values in the `settings` table. For
example, to rotate the API key:

```bash
curl -X PUT -u admin:currentpassword \
  -H "Content-Type: application/json" \
  -d '{"value": "<new api key>"}' \
  http://127.0.0.1:5000/admin/settings/api_key
```

After rotating, retrieve the new key with `python scripts/get_api_key.py`.

To change the admin password, first compute the SHA-256 hash of the new
password and update `admin_password_hash` in the same way:

```bash
curl -X PUT -u admin:currentpassword \
  -H "Content-Type: application/json" \
  -d '{"value": "<sha256 hash>"}' \
  http://127.0.0.1:5000/admin/settings/admin_password_hash
```
