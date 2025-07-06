# app.py
from utils.logger import configure_logger
configure_logger()

import logging
import threading
import time
from controllers.qr_scanner import listen_for_scans
from controllers.code_cleanup import cleanup_expired_codes
from models import init_db
import logging

logger = logging.getLogger(__name__)
logger.info("===== APP STARTED =====")
print("===== PRINT STATEMENT FOR DEBUGGING =====")

def start_flask():
    from flask_server import app as flask_app
    """Run the Flask server in a separate thread."""
    flask_app.run(debug=True, use_reloader=False)


def cleanup_scheduler():
    """Run cleanup job every 24 hours."""
    while True:
        cleanup_expired_codes()
        time.sleep(24 * 3600)

if __name__ == "__main__":
    try:
        # Start the Flask server in a separate thread
        threading.Thread(target=start_flask, daemon=True).start()
        logger.info("Flask server started")

        # Start cleanup scheduler
        threading.Thread(target=cleanup_scheduler, daemon=True).start()
        logger.info("Cleanup scheduler started")

        # Initialize the database (create all tables)
        init_db()
        logger.info("Database initialized")
    
        # Start the QR code scanning process
        listen_for_scans()

    except KeyboardInterrupt:
        # Clean up GPIO resources on program exit
        logger.info("Exiting program. Cleaning up GPIO...")
        #GPIO.cleanup()



