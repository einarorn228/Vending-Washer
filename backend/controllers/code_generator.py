import logging
import random
import string

from datetime import datetime, timedelta
from backend.models import session
from backend.models.code_model import Code
from backend.models.setting_model import get_setting_value
import logging

logger = logging.getLogger(__name__)


def generate_random_code(length=8):
    """Generate a random alphanumeric code."""
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


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
    """Generate a new QR code respecting expiration settings."""
    # Check if the order ID already exists
    existing_code = session.query(Code).filter_by(order_id=order_id).first()
    if existing_code:
        logger.warning("Order ID already exists", extra={"order_id": order_id})
        return {
            "error": "Order ID already exists",
            "code": existing_code.code,
            "usage_limit": existing_code.usage_limit,
            "current_usage": existing_code.current_usage,
            "status_code": 400,
        }

    # Generate a new unique QR code
    random_code = generate_unique_code()

    # Determine expiration policy from settings
    try:
        days = int(get_setting_value(session, "code_expiration_days", default=0))
    except (TypeError, ValueError):
        days = 0
    expiration_date = None
    if days > 0:
        expiration_date = datetime.utcnow() + timedelta(days=days)

    # Save the new QR code and usage info to the database
    new_code = Code(
        code=random_code,
        order_id=order_id,
        usage_limit=usage_limit,
        current_usage=0,
        expiration_date=expiration_date,
    )
    session.add(new_code)
    session.commit()
    logger.info(
        "Generated new code",
        extra={
            "order_id": order_id,
            "code": random_code,
            "expiration_date": expiration_date,
        },
    )

    return {
        "message": "QR code generated successfully.",
        "code": random_code,
        "order_id": order_id,
        "usage_info": {"usage_limit": usage_limit, "current_usage": 0},
        "status_code": 201,
        "expiration_date": expiration_date.isoformat() if expiration_date else None,
    }
