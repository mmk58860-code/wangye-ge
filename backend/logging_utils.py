import datetime

from .database import SessionLocal
from .models import BEIJING_TZ, SystemLog


LOG_RETENTION_HOURS = 48


def cleanup_old_logs(db=None):
    owns_session = db is None
    db = db or SessionLocal()
    try:
        cutoff = datetime.datetime.now(BEIJING_TZ) - datetime.timedelta(hours=LOG_RETENTION_HOURS)
        db.query(SystemLog).filter(SystemLog.timestamp < cutoff).delete()
        if owns_session:
            db.commit()
    finally:
        if owns_session:
            db.close()


def write_log(level: str, message: str, module: str):
    db = SessionLocal()
    try:
        cleanup_old_logs(db)
        db.add(SystemLog(level=level, message=message, module=module))
        db.commit()
    finally:
        db.close()
