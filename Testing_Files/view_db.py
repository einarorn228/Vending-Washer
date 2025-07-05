import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models import session
from models.code_model import Code

# Query all records in the codes table
codes = session.query(Code).all()

# Print the codes and their details
if codes:
    for code in codes:
        print(f"Code: {code.code}, Order ID: {code.order_id}, Usage Limit: {code.usage_limit}, Current Usage: {code.current_usage}")
else:
    print("No codes found.")

session.close()
