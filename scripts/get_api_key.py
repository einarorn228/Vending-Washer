from models import session
from models.setting_model import get_setting_value

if __name__ == "__main__":
    key = get_setting_value(session, "api_key")
    if key:
        print(key)
    else:
        print("API key not found. Run seed_settings.py first.")

