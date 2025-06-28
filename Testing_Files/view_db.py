<<<<<<< HEAD
from models.models import session, Code
=======
from Project_Files.models import session, Code
>>>>>>> 18712c10707d4f90789e158f42e4eb9880f3771e

# Query all records in the codes table
codes = session.query(Code).all()

# Print the codes and their details
for code in codes:
    print(f"Code: {code.code}, Order ID: {code.order_id}, Usage Limit: {code.usage_limit}, Current Usage: {code.current_usage}")