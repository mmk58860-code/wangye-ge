import datetime
import re
import time
from dataclasses import dataclass, field
from typing import Any

import pytz

from .api_manager import normalize_dwellir_key
from .logging_utils import write_log
from .models import BEIJING_TZ


BLOCK_SECONDS = 12
RAO_PER_TAO = 1_000_000_000
MAX_BLOCKS_PER_SCAN = 500


def amount_to_float(value: Any) -> float:
    if value is None:
        return 0
    if hasattr(value, "tao"):
        return float(value.tao)
    if isinstance(value, str):
        numeric = re.sub(r"[^0-9.]", "", value)
        if not numeric:
            return 0
        return float(numeric)
    if isinstance(value, int):
        return value / RAO_PER_TAO if value > 1_000_000 else float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def event_field(event: Any, *names: str):
    if isinstance(event, dict):
        cursor = event
        for name in names:
            cursor = cursor.get(name, {})
        return cursor or None

    cursor = event
    for name in names:
        cursor = getattr(cursor, name, None)
        if cursor is None:
            return None
    return cursor


def event_module_and_name(event: Any):
    module = event_field(event, "event", "module_id") or event_field(event, "event_module") or ""
    name = event_field(event, "event", "event_id") or event_field(event, "event_id") or ""
    return str(module), str(name)


def event_attributes(event: Any):
    attrs = event_field(event, "event", "attributes") or event_field(event, "params") or []
    if isinstance(attrs, dict):
        return [{"name": key, "value": value} for key, value in attrs.items()]
    return attrs


def extract_amounts(event: Any):
    tao_total = 0.0
    alpha_total = 0.0
    fallback_amounts = []

    for attr in event_attributes(event):
        if isinstance(attr, dict):
            name = str(attr.get("name", "")).lower()
            value = attr.get("value")
        else:
            name = str(getattr(attr, "name", "")).lower()
            value = getattr(attr, "value", None)

        amount = amount_to_float(value)
        if amount <= 0:
            continue

        if "alpha" in name:
            alpha_total += amount
        elif "tao" in name or "amount" in name or "stake" in name:
            tao_total += amount
        else:
            fallback_amounts.append(amount)

    if tao_total == 0 and alpha_total == 0 and fallback_amounts:
        tao_total = max(fallback_amounts)

    return tao_total, alpha_total


@dataclass
class DailyStakeStats:
    date: str = ""
    start_block: int = 0
    scanned_to_block: int = 0
    current_block: int = 0
    stake_tao: float = 0
    unstake_tao: float = 0
    stake_alpha: float = 0
    unstake_alpha: float = 0
    stake_events: int = 0
    unstake_events: int = 0
    updated_at: float = 0
    scanning: bool = False
    last_error: str = ""
    samples: list[str] = field(default_factory=list)

    def reset_for_today(self, current_block: int):
        now = datetime.datetime.now(BEIJING_TZ)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elapsed_seconds = max(0, int((now - midnight).total_seconds()))
        self.date = now.strftime("%Y-%m-%d")
        self.start_block = max(0, current_block - int(elapsed_seconds / BLOCK_SECONDS) - 10)
        self.scanned_to_block = self.start_block
        self.current_block = current_block
        self.stake_tao = 0
        self.unstake_tao = 0
        self.stake_alpha = 0
        self.unstake_alpha = 0
        self.stake_events = 0
        self.unstake_events = 0
        self.samples = []
        self.last_error = ""

    def as_dict(self):
        done = self.current_block > 0 and self.scanned_to_block >= self.current_block
        return {
            "date": self.date,
            "timezone": "Asia/Shanghai",
            "start_block": self.start_block,
            "scanned_to_block": self.scanned_to_block,
            "current_block": self.current_block,
            "stake_tao": self.stake_tao,
            "unstake_tao": self.unstake_tao,
            "stake_alpha": self.stake_alpha,
            "unstake_alpha": self.unstake_alpha,
            "stake_events": self.stake_events,
            "unstake_events": self.unstake_events,
            "updated_at": self.updated_at,
            "scanning": self.scanning,
            "complete": done,
            "last_error": self.last_error,
            "samples": self.samples[-10:],
        }


class DailyStakeStatsManager:
    def __init__(self):
        self.stats = DailyStakeStats()

    def scan(self, api_key: str):
        if self.stats.scanning:
            return self.stats.as_dict()

        self.stats.scanning = True
        try:
            import bittensor as bt

            endpoint = f"wss://api-bittensor-mainnet.n.dwellir.com/{normalize_dwellir_key(api_key)}"
            subtensor_cls = getattr(bt, "Subtensor", None) or getattr(bt, "subtensor")
            subtensor = subtensor_cls(network=endpoint)
            substrate = getattr(subtensor, "substrate", None)
            if substrate is None:
                raise RuntimeError("Bittensor SDK 未暴露 substrate 连接，无法扫描事件。")

            current_block = int(subtensor.get_current_block())
            today = datetime.datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
            if self.stats.date != today or self.stats.current_block == 0:
                self.stats.reset_for_today(current_block)
            else:
                self.stats.current_block = current_block

            scan_end = min(current_block, self.stats.scanned_to_block + MAX_BLOCKS_PER_SCAN)
            for block_number in range(self.stats.scanned_to_block + 1, scan_end + 1):
                block_hash = substrate.get_block_hash(block_number)
                events = substrate.get_events(block_hash=block_hash)
                for event in events:
                    module, name = event_module_and_name(event)
                    event_key = f"{module}.{name}".lower()
                    if "stakeadded" in event_key or "stake_added" in event_key:
                        tao, alpha = extract_amounts(event)
                        self.stats.stake_tao += tao
                        self.stats.stake_alpha += alpha
                        self.stats.stake_events += 1
                        if len(self.stats.samples) < 10:
                            self.stats.samples.append(f"{block_number} {module}.{name} +{tao:.6f} TAO")
                    elif "stakeremoved" in event_key or "stake_removed" in event_key:
                        tao, alpha = extract_amounts(event)
                        self.stats.unstake_tao += tao
                        self.stats.unstake_alpha += alpha
                        self.stats.unstake_events += 1
                        if len(self.stats.samples) < 10:
                            self.stats.samples.append(f"{block_number} {module}.{name} -{tao:.6f} TAO")

                self.stats.scanned_to_block = block_number

            self.stats.updated_at = time.time()
            if self.stats.scanned_to_block >= current_block:
                write_log("INFO", "北京时间当日质押/解质押统计扫描完成。", "stake_stats")
            else:
                write_log(
                    "INFO",
                    f"北京时间当日质押/解质押统计扫描进度: {self.stats.scanned_to_block}/{current_block}",
                    "stake_stats",
                )
        except Exception as e:
            self.stats.last_error = str(e)
            write_log("ERROR", f"质押/解质押统计失败: {e}", "stake_stats")
        finally:
            self.stats.scanning = False

        return self.stats.as_dict()


daily_stake_stats = DailyStakeStatsManager()
