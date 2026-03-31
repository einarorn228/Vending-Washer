import logging
import threading
import time

from backend.utils.logger import configure_logger
from backend.models import init_db
from backend.setup.seed_settings import bootstrap_settings
from backend.setup.seed_machines import bootstrap_devices_and_machines
from backend.models.setting_model import ensure_backend_relay_setting_exists

logger = logging.getLogger(__name__)


def initialize_runtime() -> None:
    """Perform one-time startup bootstrap for the full runtime."""

    configure_logger()
    init_db()
    bootstrap_settings(logger=logger)
    bootstrap_devices_and_machines(logger=logger)
    ensure_backend_relay_setting_exists()
    logger.info("===== APP STARTED =====")


def start_flask():
    from backend.flask_server import app as flask_app, configure_flask_runtime

    configure_flask_runtime(flask_app)
    flask_app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)


def cleanup_scheduler():
    from backend.controllers.code_cleanup import cleanup_expired_codes

    time.sleep(5)
    while True:
        cleanup_expired_codes()
        time.sleep(24 * 3600)


def start_background_services() -> None:
    from backend.controllers.machine_control import register_store_listeners
    from backend.controllers.qr_scanner import start_scanner_listener
    from backend.controllers.telemetry import start_telemetry_poll
    from backend.services.reisa_retry_service import run_retry_worker_loop

    register_store_listeners()

    start_telemetry_poll()
    logger.info("Telemetry polling started")

    threading.Thread(target=cleanup_scheduler, daemon=True).start()
    logger.info("Cleanup scheduler started")

    threading.Thread(target=run_retry_worker_loop, daemon=True).start()
    logger.info("Reisa retry worker thread started (settings-gated)")

    start_scanner_listener()


if __name__ == "__main__":
    try:
        initialize_runtime()

        # Start the Flask server in a separate thread
        threading.Thread(target=start_flask, daemon=True).start()
        logger.info("Flask server started")

        start_background_services()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        # Clean up GPIO resources on program exit
        logger.info("Exiting program. Cleaning up GPIO...")
        # GPIO.cleanup()
