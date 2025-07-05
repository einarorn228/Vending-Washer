import logging
import threading
from controllers.qr_scanner import listen_for_scans
from models import init_db
from utils.logger import configure_logger

configure_logger()
logger = logging.getLogger(__name__)

def start_flask():
    from flask_server import app as flask_app
    """Run the Flask server in a separate thread."""
    flask_app.run(debug=True, use_reloader=False)

if __name__ == "__main__":
    try:
        # Start the Flask server in a separate thread
        threading.Thread(target=start_flask, daemon=True).start()
        logger.info("Flask server started")

        # Initialize the database (create all tables)
        init_db()
        logger.info("Database initialized")
    
        # Start the QR code scanning process
        listen_for_scans()

    except KeyboardInterrupt:
        # Clean up GPIO resources on program exit
        logger.info("Exiting program. Cleaning up GPIO...")
        #GPIO.cleanup()


