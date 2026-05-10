import requests
from .database import SessionLocal
from .models import Setting

def get_setting(key, default=None):
    db = SessionLocal()
    try:
        s = db.query(Setting).filter(Setting.key == key).first()
        return s.value if s else default
    finally:
        db.close()

def send_telegram_notification(message):
    token = get_setting("tg_bot_token")
    chat_id = get_setting("tg_chat_id")
    
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send TG notification: {e}")
