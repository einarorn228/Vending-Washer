import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import session
from models.code_model import Code
from models.setting_model import Settings

def print_codes(limit=None):
    query = session.query(Code)
    if limit:
        query = query.limit(limit)
    codes = query.all()
    if codes:
        for code in codes:
            print(f"Code: {code.code}, Order ID: {code.order_id}, Usage Limit: {code.usage_limit}, Current Usage: {code.current_usage}")
    else:
        print("No codes found.")

def print_settings(limit=None):
    query = session.query(Settings)
    if limit:
        query = query.limit(limit)
    settings = query.all()
    if settings:
        for setting in settings:
            print(f"Key: {setting.key}, Value: {setting.value}")
    else:
        print("No settings found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View database tables.")
    parser.add_argument('--table', choices=['codes', 'settings'], default='codes', help='Table to view (default: codes)')
    parser.add_argument('--limit', type=int, default=None, help='Number of rows to display (default: all)')
    args = parser.parse_args()

    if args.table == 'codes':
        print_codes(args.limit)
    elif args.table == 'settings':
        print_settings(args.limit)

    session.close()
