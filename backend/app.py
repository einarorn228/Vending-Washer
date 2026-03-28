import logging
import threading
import time

from backend.utils.logger import configure_logger
from backend.models import init_db
from backend.setup.seed_settings import bootstrap_settings
from backend.setup.seed_machines import bootstrap_devices_and_machines
from backend.models.setting_model import ensure_backend_relay_setting_exists

configure_logger()
init_db()
bootstrap_settings()
bootstrap_devices_and_machines()
ensure_backend_relay_setting_exists()

logger = logging.getLogger(__name__)
logger.info("===== APP STARTED =====")

# Now import modules that use the DB
from backend.controllers.code_cleanup import cleanup_expired_codes
from backend.controllers.qr_scanner import start_scanner_listener
from backend.controllers.telemetry import start_telemetry_poll
from backend.services.reisa_retry_service import run_retry_worker_loop


def start_flask():
    from backend.flask_server import app as flask_app
    flask_app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)


def cleanup_scheduler():
    time.sleep(5)
    while True:
        cleanup_expired_codes()
        time.sleep(24 * 3600)


if __name__ == "__main__":
    try:
        # Start the Flask server in a separate thread
        threading.Thread(target=start_flask, daemon=True).start()
        logger.info("Flask server started")

        # Start telemetry polling
        start_telemetry_poll()
        logger.info("Telemetry polling started")

        # Start cleanup scheduler
        threading.Thread(target=cleanup_scheduler, daemon=True).start()
        logger.info("Cleanup scheduler started")

        # Optional guarded auto-retry worker (disabled by default in settings).
        threading.Thread(target=run_retry_worker_loop, daemon=True).start()
        logger.info("Reisa retry worker thread started (settings-gated)")

        # Start the QR code scanning process
        start_scanner_listener()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        # Clean up GPIO resources on program exit
        logger.info("Exiting program. Cleaning up GPIO...")
        # GPIO.cleanup()
