import asyncio
import aiohttp
import time
import random
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from .models import ApiKey, SystemLog, get_beijing_time
from .database import SessionLocal

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
                if k.key_value not in self.buckets:
                    self.buckets[k.key_value] = TokenBucket(k.requests_per_second, k.requests_per_second)
                else:
                    # Update rate if changed
                    self.buckets[k.key_value].rate = k.requests_per_second
                    self.buckets[k.key_value].capacity = k.requests_per_second
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
            
            if await self.buckets[key.key_value].consume():
                if await self.global_bucket.consume():
                    return key
        
        # If no key available immediately, wait a bit
        await asyncio.sleep(0.1)
        return await self.get_next_available_key()

    async def call_rpc(self, method: str, params: list = [], retries: int = 3) -> Optional[dict]:
        for attempt in range(retries):
            key_obj = await self.get_next_available_key()
            if not key_obj:
                print("No API keys available.")
                return None

            url = f"https://api-bittensor-mainnet.n.dwellir.com/{key_obj.key_value}"
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
                                print(f"RPC Error: {data.get('error')}")
                        elif response.status == 429:
                            print(f"Rate limited on key {key_obj.key_value[:8]}...")
                        else:
                            print(f"HTTP Error {response.status} on key {key_obj.key_value[:8]}...")
            except Exception as e:
                print(f"Request Exception: {e}")
            
            await asyncio.sleep(0.5 * (attempt + 1))
        
        return None

api_manager = ApiPoolManager()
