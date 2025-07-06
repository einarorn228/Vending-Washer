from datetime import datetime
import logging
from models import session, Code
import logging

logger = logging.getLogger(__name__)


def cleanup_expired_codes():
    """Remove codes whose expiration_date has passed."""
    expired_codes = (
        session.query(Code)
        .filter(Code.expiration_date.isnot(None))
        .filter(Code.expiration_date <= datetime.utcnow())
        .all()
    )
    
    if expired_codes:
        for code in expired_codes:
            logger.info("Removing expired code: %s", code.code)
            session.delete(code)
        session.commit()
    else:
        logger.info("No expired codes to clean up.")
