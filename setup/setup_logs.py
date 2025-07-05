import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

def setup_logs():
    os.makedirs(LOG_DIR, exist_ok=True)
    os.chmod(LOG_DIR, 0o755)
    log_file = os.path.join(LOG_DIR, "app.log")
    if not os.path.exists(log_file):
        open(log_file, "a").close()
        os.chmod(log_file, 0o644)
        print(f"Created log directory and file at {LOG_DIR}")
    else:
        print(f"Log directory already exists at {LOG_DIR}")


if __name__ == "__main__":
    setup_logs()
