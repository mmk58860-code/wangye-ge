from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio
from typing import List

from .database import get_db, init_db
from .models import ApiKey, Setting, SystemLog, get_beijing_time
from .api_manager import api_manager
from .data_fetcher import data_update_loop, subnet_data_manager
from .event_monitor import event_monitor

app = FastAPI(title="Bittensor Dashboard API")

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
    # Start background tasks
    asyncio.create_task(data_update_loop())
    asyncio.create_task(event_monitor.start())
    api_manager.refresh_keys()

@app.get("/api/subnets")
async def get_subnets():
    return list(subnet_data_manager.subnets.values())

@app.get("/api/racing")
async def get_racing():
    return subnet_data_manager.get_racing_stats()

@app.get("/api/logs")
async def get_logs(db: Session = Depends(get_db)):
    # Get last 100 logs
    logs = db.query(SystemLog).order_by(SystemLog.timestamp.desc()).limit(100).all()
    return logs

@app.get("/api/settings")
async def get_settings(db: Session = Depends(get_db)):
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}

@app.post("/api/settings")
async def update_settings(data: dict, db: Session = Depends(get_db)):
    for key, value in data.items():
        s = db.query(Setting).filter(Setting.key == key).first()
        if s:
            s.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    db.commit()
    return {"status": "success"}

@app.get("/api/api-keys")
async def get_api_keys(db: Session = Depends(get_db)):
    return db.query(ApiKey).all()

@app.post("/api/api-keys")
async def add_api_key(data: dict, db: Session = Depends(get_db)):
    new_key = ApiKey(
        key_value=data["key_value"],
        description=data.get("description", ""),
        requests_per_second=data.get("requests_per_second", 20)
    )
    db.add(new_key)
    db.commit()
    api_manager.refresh_keys()
    return {"status": "success"}

@app.delete("/api/api-keys/{key_id}")
async def delete_api_key(key_id: int, db: Session = Depends(get_db)):
    db.query(ApiKey).filter(ApiKey.id == key_id).delete()
    db.commit()
    api_manager.refresh_keys()
    return {"status": "success"}
