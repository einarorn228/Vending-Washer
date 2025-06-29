
from models.models import session, Code

# Query all records in the codes table
codes = session.query(Code).all()

# Print the codes and their details
for code in codes:
    print(f"Code: {code.code}, Order ID: {code.order_id}, Usage Limit: {code.usage_limit}, Current Usage: {code.current_usage}")
