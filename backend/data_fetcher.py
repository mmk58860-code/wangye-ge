import asyncio
import time
from .api_manager import api_manager
from .models import SystemLog, get_beijing_time
from .database import SessionLocal
import json

class SubnetData:
    def __init__(self):
        self.subnets = {}
        self.last_update = 0
        self.current_block = 0
        self.immunity_period = 0
        self.lock = asyncio.Lock()

    async def update_data(self):
        async with self.lock:
            # 1. Fetch current block height
            block_data = await api_manager.call_rpc("eth_blockNumber")
            if block_data:
                self.current_block = int(block_data, 16)

            # 2. Fetch hyperparams for immunity period (assuming it's global or from a specific netuid)
            # For simplicity, we can fetch it once or periodically. 
            # In Bittensor, it's often netuid 0 or specific to each subnet.
            # Let's assume we fetch all dynamic info which contains most of what we need.
            
            dynamic_info = await api_manager.call_rpc("subnetInfo_getAllDynamicInfo")
            if dynamic_info:
                new_subnets = {}
                for info in dynamic_info:
                    netuid = info.get('netuid')
                    new_subnets[netuid] = {
                        "name": info.get('name', f"Subnet {netuid}"),
                        "netuid": netuid,
                        "alpha_price": info.get('alphaPrice', 0),
                        "registration_cost": info.get('burn', 0),
                        "ema": info.get('ema', 0),
                        "registration_block": info.get('registrationBlock', 0),
                        "immunity_period": info.get('immunityPeriod', 5000), # Default if missing
                        "is_immune": False
                    }
                    
                    # Calculate immunity
                    if self.current_block - new_subnets[netuid]["registration_block"] < new_subnets[netuid]["immunity_period"]:
                        new_subnets[netuid]["is_immune"] = True
                        new_subnets[netuid]["immunity_left"] = new_subnets[netuid]["immunity_period"] - (self.current_block - new_subnets[netuid]["registration_block"])
                    else:
                        new_subnets[netuid]["immunity_left"] = 0

                self.subnets = new_subnets
                self.last_update = time.time()
                
    def get_racing_stats(self):
        total_subnets = len(self.subnets)
        non_immune = [s for s in self.subnets.values() if not s["is_immune"]]
        immune = [s for s in self.subnets.values() if s["is_immune"]]
        
        # Sort non-immune by EMA to find eviction candidate (lowest EMA is at risk)
        non_immune_sorted = sorted(non_immune, key=lambda x: x["ema"])
        eviction_candidate = non_immune_sorted[0] if non_immune_sorted else None
        
        return {
            "total_count": total_subnets,
            "max_capacity": 128,
            "non_immune_count": len(non_immune),
            "eviction_candidate": eviction_candidate,
            "immune_list": immune,
            "current_block": self.current_block
        }

subnet_data_manager = SubnetData()

async def data_update_loop():
    while True:
        try:
            await subnet_data_manager.update_data()
        except Exception as e:
            print(f"Error in data update loop: {e}")
        await asyncio.sleep(60) # Update every minute
