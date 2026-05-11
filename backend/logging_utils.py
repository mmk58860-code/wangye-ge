from .database import SessionLocal
from .models import SystemLog


def write_log(level: str, message: str, module: str):
    db = SessionLocal()
    try:
        db.add(SystemLog(level=level, message=message, module=module))
        db.commit()
    finally:
        db.close()
