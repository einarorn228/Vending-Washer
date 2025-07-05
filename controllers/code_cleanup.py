from datetime import datetime
import logging

from models import session, Code
from models.setting_model import get_setting_value
from utils.logger import configure_logger

configure_logger()
logger = logging.getLogger(__name__)

def cleanup_expired_codes():
    """Remove fully used codes from the database based on the expiration date."""
    expiration_days = int(get_setting_value(session, "code_expiration_days", default=30))
    logger.debug("Expiration threshold: %s days", expiration_days)
    expired_codes = session.query(Code).filter(Code.expiration_date <= datetime.now()).all()
    
    if expired_codes:
        for code in expired_codes:
            logger.info("Removing expired code: %s", code.code)
            session.delete(code)
        session.commit()
    else:
        logger.info("No expired codes to clean up.")
