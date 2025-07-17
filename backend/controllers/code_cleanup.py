from datetime import datetime
import logging
from models import session
from models.code_model import Code
from models.scan_log_model import ScanLog

logger = logging.getLogger(__name__)


def cleanup_expired_codes():
    """Remove codes whose expiration_date has passed and their scan logs."""
    expired_codes = (
        session.query(Code)
        .filter(Code.expiration_date.isnot(None))
        .filter(Code.expiration_date <= datetime.utcnow())
        .all()
    )

    if expired_codes:
        for code in expired_codes:
            logger.info("Removing expired code: %s", code.code)
            # Delete associated scan logs
            deleted_logs = (
                session.query(ScanLog).filter(ScanLog.code == code.code).delete()
            )
            if deleted_logs:
                logger.info(
                    "Removed %d scan logs for code: %s", deleted_logs, code.code
                )
            session.delete(code)
        session.commit()
    else:
        logger.info("No expired codes to clean up.")
