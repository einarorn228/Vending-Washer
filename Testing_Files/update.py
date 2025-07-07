import sqlite3
from models import session
from models.setting_model import update_setting_value

update_setting_value(session, "expired_code_cleanup_days", "0",)
session.commit()

#conn = sqlite3.connect('codes.db')  # Use your actual DB path
#c = conn.cursor()
#c.execute("ALTER TABLE codes ADD COLUMN created_at DATETIME")
#conn.commit()
#conn.close()