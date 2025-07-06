# Vending Washer

This project powers a simple QR-code based vending washer prototype.

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