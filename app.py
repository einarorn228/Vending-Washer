from controllers.qr_scanner import listen_for_scans
from controllers.code_cleanup import cleanup_expired_codes
from models import init_db
import threading
import RPi.GPIO as GPIO

def start_flask():
    from flask_server import app as flask_app
    """Run the Flask server in a separate thread."""
    flask_app.run(debug=True, use_reloader=False)

def start_cleanup_schedule():
    from apscheduler.schedulers.background import BackgroundScheduler
    """Start the daily cleanup schedule to remove expired codes."""
    scheduler = BackgroundScheduler()
    # Schedule `cleanup_expired_codes` to run daily at midnight
    scheduler.add_job(cleanup_expired_codes, 'interval', days=1)
    scheduler.start()

def start_monitor_buttons():
    from controllers.machine_control import monitor_buttons
    """Start monitoring buttons to control machines."""
    try:
        monitor_buttons()
    except Exception as e:
        print(f"Error in button monitor: {e}")

if __name__ == "__main__":
    try:    
        # Start the Flask server in a separate thread
        flask_thread = threading.Thread(target=start_flask)
        flask_thread.start()

        # Start monitoring buttons in a separate thread
        buttons_thread = threading.Thread(target=start_monitor_buttons)
        buttons_thread.start()

        # Initialize the database (create all tables)
        init_db()

        # Start the daily cleanup scheduler
        start_cleanup_schedule()

        # Start the QR code scanning process
        listen_for_scans()

    except KeyboardInterrupt:
        # Clean up GPIO resources on program exit
        print("Exiting program. Cleaning up GPIO...")
        GPIO.cleanup()


