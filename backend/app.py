import os
import subprocess
import threading
import time
import logging
import sys

from .utils.logger import configure_logger

configure_logger()

# --- Auto-setup section ---

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
if not os.path.exists(LOG_FILE):
    subprocess.run([sys.executable, "-m", "setup.seed_settings"], check=True)

from .models import init_db

init_db()
subprocess.run([sys.executable, "-m", "setup.seed_settings"], check=True)

logger = logging.getLogger(__name__)
logger.info("===== APP STARTED =====")

# Now import modules that use the DB
from .controllers.qr_scanner import listen_for_scans
from .controllers.code_cleanup import cleanup_expired_codes


def start_flask():
    from .flask_server import app as flask_app

    flask_app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)


def cleanup_scheduler():
    time.sleep(5)
    while True:
        cleanup_expired_codes()
        time.sleep(24 * 3600)


if __name__ == "__main__":
    try:
        # Initialize the database (create all tables)
        init_db()
        logger.info("Database initialized")

        # Start the Flask server in a separate thread
        threading.Thread(target=start_flask, daemon=True).start()
        logger.info("Flask server started")

        # Start cleanup scheduler
        threading.Thread(target=cleanup_scheduler, daemon=True).start()
        logger.info("Cleanup scheduler started")

        # Start the QR code scanning process
        listen_for_scans()

    except KeyboardInterrupt:
        # Clean up GPIO resources on program exit
        logger.info("Exiting program. Cleaning up GPIO...")
        # GPIO.cleanup()
