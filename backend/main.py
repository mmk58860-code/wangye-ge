from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio
from pydantic import BaseModel

from .database import get_db, init_db
from .models import ApiKey, Setting, SystemLog
from .api_manager import api_manager
from .api_manager import normalize_dwellir_key
from .data_fetcher import data_update_loop, subnet_data_manager
from .event_monitor import event_monitor
from .stake_stats import daily_stake_stats
from .security import assert_install_complete, authenticate_admin, require_admin
from .logging_utils import cleanup_old_logs, write_log

app = FastAPI(title="Bittensor Dashboard API")


class LoginRequest(BaseModel):
    username: str
    password: str

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()
    assert_install_complete()
    cleanup_old_logs()
    # Start background tasks
    asyncio.create_task(data_update_loop())
    asyncio.create_task(event_monitor.start())
    api_manager.refresh_keys()

@app.post("/api/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    token = authenticate_admin(db, data.username, data.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"token": token}

@app.get("/api/auth/check")
async def check_auth(_: bool = Depends(require_admin)):
    return {"status": "ok"}

@app.get("/api/subnets")
async def get_subnets(_: bool = Depends(require_admin)):
    return [s for s in subnet_data_manager.subnets.values() if s.get("netuid") != 0]

@app.post("/api/sync")
async def sync_data(_: bool = Depends(require_admin)):
    api_manager.refresh_keys()
    await subnet_data_manager.update_data()
    if api_manager.keys:
        await asyncio.to_thread(daily_stake_stats.scan, api_manager.keys[0].key_value)
    return {
        "status": "success",
        "subnet_count": len(subnet_data_manager.subnets),
        "current_block": subnet_data_manager.current_block,
    }

@app.get("/api/daily-stake-stats")
async def get_daily_stake_stats(_: bool = Depends(require_admin)):
    return daily_stake_stats.stats.as_dict()

@app.post("/api/daily-stake-stats/sync")
async def sync_daily_stake_stats(_: bool = Depends(require_admin)):
    api_manager.refresh_keys()
    if not api_manager.keys:
        raise HTTPException(status_code=400, detail="No Dwellir API Key configured")
    return await asyncio.to_thread(daily_stake_stats.scan, api_manager.keys[0].key_value)

@app.get("/api/racing")
async def get_racing(_: bool = Depends(require_admin)):
    return subnet_data_manager.get_racing_stats()

@app.get("/api/logs")
async def get_logs(_: bool = Depends(require_admin), db: Session = Depends(get_db)):
    # Get last 100 logs
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(100).all()
    return logs

@app.get("/api/settings")
async def get_settings(_: bool = Depends(require_admin), db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}

@app.post("/api/settings")
async def update_settings(data: dict, _: bool = Depends(require_admin), db: Session = Depends(get_db)):
    for key, value in data.items():
        s = db.query(Setting).filter(Setting.key == key).first()
        if s:
            s.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    db.commit()
    return {"status": "success"}

@app.get("/api/api-keys")
async def get_api_keys(_: bool = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(ApiKey).all()

@app.post("/api/api-keys")
async def add_api_key(data: dict, _: bool = Depends(require_admin), db: Session = Depends(get_db)):
    key_value = normalize_dwellir_key(data["key_value"])
    new_key = ApiKey(
        key_value=key_value,
        description=data.get("description", ""),
        requests_per_second=data.get("requests_per_second", 20)
    )
    db.add(new_key)
    db.commit()
    api_manager.refresh_keys()
    write_log("INFO", "已添加 Dwellir API Key。", "api_manager")
    return {"status": "success"}

@app.delete("/api/api-keys/{key_id}")
async def delete_api_key(key_id: int, _: bool = Depends(require_admin), db: Session = Depends(get_db)):
    db.query(ApiKey).filter(ApiKey.id == key_id).delete()
    db.commit()
    api_manager.refresh_keys()
    return {"status": "success"}
