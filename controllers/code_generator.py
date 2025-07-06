import logging
import random
import string

from models import session
from models.code_model import Code
import logging

logger = logging.getLogger(__name__)

def generate_random_code(length=8):
    """Generate a random alphanumeric code."""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def is_code_unique(code_value):
    """Check if the generated code already exists in the database."""
    existing_code = session.query(Code).filter_by(code=code_value).first()
    return existing_code is None

def generate_unique_code(length=8):
    """Generate a unique QR code that doesn't already exist in the database."""
    while True:
        random_code = generate_random_code(length)
        logger.debug("Generated candidate code", extra={"code": random_code})
        if is_code_unique(random_code):
            return random_code

def generate_new_code(order_id, usage_limit):
    
    """Main logic for generating a new QR code."""
    # Check if the order ID already exists
    existing_code = session.query(Code).filter_by(order_id=order_id).first()
    if existing_code:
        logger.warning("Order ID already exists", extra={"order_id": order_id})
        return {
            "error": "Order ID already exists",
            "code": existing_code.code,
            "usage_limit": existing_code.usage_limit,
            "current_usage": existing_code.current_usage,
            "status_code": 400
        }

    # Generate a new unique QR code
    random_code = generate_unique_code()

    # Save the new QR code and usage info to the database
    new_code = Code(code=random_code, order_id=order_id, usage_limit=usage_limit, current_usage=0)
    session.add(new_code)
    session.commit()
    logger.info("Generated new code", extra={"order_id": order_id, "code": random_code})

    return {
        "message": "QR code generated successfully.",
        "code": random_code,
        "order_id": order_id,
        "usage_info": {
            "usage_limit": usage_limit,
            "current_usage": 0
        },
        "status_code": 201
    }
