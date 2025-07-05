import os

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
    print(f"Created log directory at {LOG_DIR}")
else:
    print(f"Log directory already exists at {LOG_DIR}")
