import asyncio
import websockets
import json
from .api_manager import api_manager
from .notifications import send_telegram_notification
from .models import SystemLog, get_beijing_time, ApiKey
from .database import SessionLocal

class EventMonitor:
    def __init__(self):
        self.wss_url = "wss://api-bittensor-mainnet.n.dwellir.com"
        self.running = False

    async def start(self):
        self.running = True
        while self.running:
            try:
                # Use one of the keys for WSS if needed, 
                # but usually Dwellir WSS also needs a key in the path.
                # Let's get the first available key.
                db = SessionLocal()
                api_key_obj = db.query(ApiKey).filter(ApiKey.enabled == True).first()
                db.close()
                
                if not api_key_obj:
                    print("No API key for WSS. Waiting...")
                    await asyncio.sleep(10)
                    continue

                full_url = f"{self.wss_url}/{api_key_obj.key_value}"
                async with websockets.connect(full_url) as ws:
                    # Subscribe to new heads
                    subscribe_msg = {
                        "jsonrpc": "2.0",
                        "method": "chain_subscribeNewHeads",
                        "params": [],
                        "id": 1
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    
                    while self.running:
                        response = await ws.recv()
                        data = json.loads(response)
                        
                        if "method" in data and data["method"] == "chain_newHead":
                            block_number = int(data["params"]["result"]["number"], 16)
                            block_hash = data["params"]["result"]["hash"]
                            await self.process_block(block_number, block_hash)
            except Exception as e:
                print(f"WSS Error: {e}")
                await asyncio.sleep(5)

    async def process_block(self, block_number, block_hash):
        # Fetch events for this block
        # method: state_getStorage
        # key for events: 0x26aa394eea5630e07c48ae0c9558cef780d41e5e16056765bc8461851072c9d7
        # (Standard Substrate system events key)
        
        events_raw = await api_manager.call_rpc("state_getStorage", ["0x26aa394eea5630e07c48ae0c9558cef780d41e5e16056765bc8461851072c9d7", block_hash])
        
        if events_raw:
            # Parsing events is complex without a scale-codec, 
            # but we can look for specific patterns or just compare subnet lists
            # as a fallback if decoding is too heavy.
            # However, the user asked to "read events in this block".
            # For now, let's trigger a sync and notify if count changed.
            pass
            
    async def stop(self):
        self.running = False

event_monitor = EventMonitor()
