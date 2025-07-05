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

