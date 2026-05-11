import asyncio
import time
from .api_manager import api_manager
from .api_manager import normalize_dwellir_key
from .models import SystemLog, get_beijing_time
from .database import SessionLocal
from .logging_utils import write_log
import json


def balance_to_float(value):
    if value is None:
        return 0
    if hasattr(value, "tao"):
        return float(value.tao)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def fetch_with_bittensor_sdk(api_key: str):
    import bittensor as bt

    endpoint = f"wss://api-bittensor-mainnet.n.dwellir.com/{normalize_dwellir_key(api_key)}"
    subtensor_cls = getattr(bt, "Subtensor", None) or getattr(bt, "subtensor")
    subtensor = subtensor_cls(network=endpoint)
    current_block = subtensor.get_current_block()
    dynamic_subnets = subtensor.all_subnets()

    if not dynamic_subnets:
        return current_block, {}

    parsed = {}
    for subnet in dynamic_subnets:
        netuid = int(getattr(subnet, "netuid", 0))
        if netuid == 0:
            continue
        registration_block = int(getattr(subnet, "network_registered_at", 0) or 0)
        immunity_period = 5000
        immunity_left = max(0, immunity_period - (current_block - registration_block))

        parsed[netuid] = {
            "name": getattr(subnet, "subnet_name", None) or f"Subnet {netuid}",
            "netuid": netuid,
            "alpha_price": balance_to_float(getattr(subnet, "price", 0)),
            "registration_cost": 0,
            "ema": balance_to_float(getattr(subnet, "moving_price", 0)),
            "registration_block": registration_block,
            "immunity_period": immunity_period,
            "is_immune": immunity_left > 0,
            "immunity_left": immunity_left,
        }

    return current_block, parsed

class SubnetData:
    def __init__(self):
        self.subnets = {}
        self.last_update = 0
        self.current_block = 0
        self.immunity_period = 0
        self.lock = asyncio.Lock()

    async def update_data(self):
        async with self.lock:
            api_manager.refresh_keys()
            if api_manager.keys:
                try:
                    current_block, sdk_subnets = await asyncio.to_thread(
                        fetch_with_bittensor_sdk,
                        api_manager.keys[0].key_value,
                    )
                    if sdk_subnets:
                        self.current_block = current_block
                        self.subnets = sdk_subnets
                        self.last_update = time.time()
                        write_log("INFO", f"SDK 子网数据同步完成，共 {len(sdk_subnets)} 个子网。", "data_fetcher")
                        return
                    write_log("WARN", "Bittensor SDK 未返回子网数据，转入 RPC 健康检查。", "data_fetcher")
                except ImportError:
                    write_log("ERROR", "缺少 bittensor SDK，请运行升级脚本安装后端依赖。", "data_fetcher")
                except Exception as e:
                    write_log("ERROR", f"Bittensor SDK 同步失败: {e}", "data_fetcher")

            # 1. Fetch current block height
            block_data = await api_manager.call_rpc("eth_blockNumber")
            if block_data:
                self.current_block = int(block_data, 16)
            else:
                write_log("WARN", "获取当前区块高度失败，请检查 Dwellir API Key。", "data_fetcher")
                return

            # 2. Fetch hyperparams for immunity period (assuming it's global or from a specific netuid)
            # For simplicity, we can fetch it once or periodically. 
            # In Bittensor, it's often netuid 0 or specific to each subnet.
            # Let's assume we fetch all dynamic info which contains most of what we need.
            
            dynamic_info = await api_manager.call_rpc("subnetInfo_getAllDynamicInfo")
            if dynamic_info:
                new_subnets = {}
                for info in dynamic_info:
                    netuid = info.get('netuid')
                    if netuid == 0:
                        continue
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
                write_log("INFO", f"子网数据同步完成，共 {len(new_subnets)} 个子网。", "data_fetcher")
            else:
                write_log("WARN", "获取子网动态数据失败，可能是 API Key 无效、接口方法不可用或网络异常。", "data_fetcher")
                
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
            write_log("ERROR", f"数据同步循环异常: {e}", "data_fetcher")
        await asyncio.sleep(60) # Update every minute
