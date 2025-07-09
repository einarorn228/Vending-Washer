import sqlite3
from models import session
from models.setting_model import update_setting_value, Settings

#api_key_setting = session.query(Settings).filter_by(key="api_key").first()
#if api_key_setting:
#    print("Current API key:", api_key_setting.value)
#else:
#    print("API key not found.")

update_setting_value(session, "cors_allowed_origins", "http://localhost, http://173.25.200.254",)
session.commit()

#conn = sqlite3.connect('codes.db')  # Use your actual DB path
#c = conn.cursor()
#c.execute("ALTER TABLE codes ADD COLUMN created_at DATETIME")
#conn.commit()
#conn.close()