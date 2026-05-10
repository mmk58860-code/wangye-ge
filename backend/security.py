import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import SessionLocal, get_db
from .models import Setting


PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 200000


def get_setting(db: Session, key: str) -> str | None:
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else None


def upsert_setting(db: Session, key: str, value: str):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        db.add(Setting(key=key, value=value))


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False

    try:
        scheme, iterations, salt, digest = stored_hash.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations),
        ).hex()
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(candidate, digest)


def configure_admin(username: str, password: str):
    db = SessionLocal()
    try:
        upsert_setting(db, "admin_user", username)
        upsert_setting(db, "admin_password_hash", hash_password(password))
        upsert_setting(db, "admin_token", secrets.token_urlsafe(32))
        db.commit()
    finally:
        db.close()


def authenticate_admin(db: Session, username: str, password: str) -> str | None:
    admin_user = get_setting(db, "admin_user")
    admin_password_hash = get_setting(db, "admin_password_hash")

    if admin_user != username or not verify_password(password, admin_password_hash):
        return None

    token = secrets.token_urlsafe(32)
    upsert_setting(db, "admin_token", token)
    db.commit()
    return token


def require_admin(
    x_admin_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    admin_token = get_setting(db, "admin_token")
    if not admin_token or not x_admin_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not hmac.compare_digest(x_admin_token, admin_token):
        raise HTTPException(status_code=401, detail="Not authenticated")

    return True
