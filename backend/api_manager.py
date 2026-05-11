import asyncio
import aiohttp
import time
import random
from typing import List, Optional, Dict
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from .models import ApiKey, SystemLog, get_beijing_time
from .database import SessionLocal
from .logging_utils import write_log


def normalize_dwellir_key(value: str) -> str:
    value = (value or "").strip().rstrip("/")
    if "://" not in value:
        return value

    parsed = urlparse(value)
    path_parts = [part for part in parsed.path.split("/") if part]
    return path_parts[-1] if path_parts else value


def mask_key(value: str) -> str:
    normalized = normalize_dwellir_key(value)
    if len(normalized) <= 12:
        return "***"
    return f"{normalized[:8]}...{normalized[-4:]}"

class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_fill = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self):
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_fill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_fill = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

class ApiPoolManager:
    def __init__(self):
        self.buckets: Dict[str, TokenBucket] = {}
        self.global_limit = 50 # Default global limit
        self.global_bucket = TokenBucket(50, 50)
        self.keys: List[ApiKey] = []
        self.current_index = 0

    def refresh_keys(self):
        db = SessionLocal()
        try:
            self.keys = db.query(ApiKey).filter(ApiKey.enabled == True).all()
            for k in self.keys:
                normalized_key = normalize_dwellir_key(k.key_value)
                if normalized_key not in self.buckets:
                    self.buckets[normalized_key] = TokenBucket(k.requests_per_second, k.requests_per_second)
                else:
                    # Update rate if changed
                    self.buckets[normalized_key].rate = k.requests_per_second
                    self.buckets[normalized_key].capacity = k.requests_per_second
        finally:
            db.close()

    async def get_next_available_key(self) -> Optional[ApiKey]:
        if not self.keys:
            self.refresh_keys()
        
        if not self.keys:
            return None

        # Try to find a key that has tokens
        for _ in range(len(self.keys)):
            key = self.keys[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.keys)
            
            normalized_key = normalize_dwellir_key(key.key_value)
            if await self.buckets[normalized_key].consume():
                if await self.global_bucket.consume():
                    return key
        
        # If no key available immediately, wait a bit
        await asyncio.sleep(0.1)
        return await self.get_next_available_key()

    async def call_rpc(self, method: str, params: Optional[list] = None, retries: int = 3) -> Optional[dict]:
        params = params or []
        for attempt in range(retries):
            key_obj = await self.get_next_available_key()
            if not key_obj:
                write_log("WARN", "没有可用的 Dwellir API Key，请先在系统设置中添加。", "api_manager")
                return None

            normalized_key = normalize_dwellir_key(key_obj.key_value)
            url = f"https://api-bittensor-mainnet.n.dwellir.com/{normalized_key}"
            payload = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": random.randint(1, 1000000)
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            if "result" in data:
                                return data["result"]
                            else:
                                write_log("ERROR", f"RPC 调用 {method} 返回错误: {data.get('error')}", "api_manager")
                        elif response.status == 429:
                            write_log("WARN", f"Dwellir API Key {mask_key(normalized_key)} 触发限流。", "api_manager")
                        else:
                            write_log("ERROR", f"RPC HTTP {response.status}: {method}, key={mask_key(normalized_key)}", "api_manager")
            except Exception as e:
                write_log("ERROR", f"RPC 请求异常: {method}: {e}", "api_manager")
            
            await asyncio.sleep(0.5 * (attempt + 1))
        
        return None

api_manager = ApiPoolManager()
