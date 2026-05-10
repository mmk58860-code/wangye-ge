from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime
import pytz

Base = declarative_base()
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    return datetime.datetime.now(BEIJING_TZ)

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key_value = Column(String, unique=True)
    description = Column(String)
    enabled = Column(Boolean, default=True)
    requests_per_second = Column(Integer, default=20)
    total_requests = Column(Integer, default=0)
    last_used = Column(DateTime)

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=get_beijing_time)
    level = Column(String) # INFO, WARN, ERROR
    message = Column(Text)
    module = Column(String)
