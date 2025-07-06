import sys
import os
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import session
from models.code_model import Code
from models.setting_model import Settings
from models.scan_log_model import ScanLog

def print_codes(limit=None, code=None, order_id=None):
    query = session.query(Code)
    if code:
        query = query.filter(Code.code == code)
    if order_id:
        query = query.filter(Code.order_id == order_id)
    if limit:
        query = query.limit(limit)
    codes = query.all()
    if codes:
        for code_obj in codes:
            print(f"Code: {code_obj.code}, Order ID: {code_obj.order_id}, Usage Limit: {code_obj.usage_limit}, Current Usage: {code_obj.current_usage}")
    else:
        print("No codes found.")

def print_settings(limit=None, key=None):
    query = session.query(Settings)
    if key:
        query = query.filter(Settings.key == key)
    if limit:
        query = query.limit(limit)
    settings = query.all()
    if settings:
        for setting in settings:
            print(f"Key: {setting.key}, Value: {setting.value}")
    else:
        print("No settings found.")

def print_scan_logs(limit=None, code=None, order_id=None):
    query = session.query(ScanLog)
    if code:
        query = query.filter(ScanLog.code == code)
    if order_id:
        query = query.filter(ScanLog.order_id == order_id)
    if limit:
        query = query.limit(limit)
    logs = query.all()
    if logs:
        for log in logs:
            print(f"ID: {log.id}, Code: {log.code}, Order ID: {log.order_id}, Time: {log.timestamp}, Result: {log.result}, Details: {log.details}")
    else:
        print("No scan logs found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View database tables.")
    parser.add_argument('--table', choices=['codes', 'settings', 'scan_logs'], default='codes', help='Table to view (default: codes)')
    parser.add_argument('--limit', type=int, default=None, help='Number of rows to display (default: all)')
    parser.add_argument('--code', type=str, default=None, help='Filter by code value')
    parser.add_argument('--order_id', type=str, default=None, help='Filter by order_id')
    parser.add_argument('--key', type=str, default=None, help='Filter settings table by key')
    args = parser.parse_args()

    if args.table == 'codes':
        print_codes(limit=args.limit, code=args.code, order_id=args.order_id)
    elif args.table == 'settings':
        print_settings(limit=args.limit, key=args.key)
    elif args.table == 'scan_logs':
        print_scan_logs(limit=args.limit, code=args.code, order_id=args.order_id)

    session.close()
