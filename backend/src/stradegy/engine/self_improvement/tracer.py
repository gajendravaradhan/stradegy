from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import json
from loguru import logger

from stradegy.config import settings


@dataclass
class TradeTrace:
    trade_id: str
    timestamp: datetime
    ticker: str
    action: str
    price: float
    shares: int
    strategy: str
    signal_confidence: float
    market_context: dict = field(default_factory=dict)
    slippage: float = 0.0
    fees: float = 0.0
    expected_outcome: str = ""
    actual_outcome: str = ""
    pnl: float | None = None


class TradeTracer:
    def __init__(self, log_dir: Path | None = None):
        self.log_dir = log_dir or settings.eval_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "trade_traces.jsonl"

    def append(self, trace: TradeTrace) -> None:
        try:
            with self.log_file.open("a") as f:
                f.write(json.dumps(asdict(trace), default=str) + "\n")
        except Exception as e:
            logger.error(f"Failed to write trade trace: {e}")

    def get_recent(self, n: int = 100) -> list[dict[str, Any]]:
        if not self.log_file.exists():
            return []
        try:
            traces = []
            with self.log_file.open("r") as f:
                for line in f:
                    if line.strip():
                        traces.append(json.loads(line))
            return traces[-n:] if len(traces) > n else traces
        except Exception as e:
            logger.error(f"Failed to read trade traces: {e}")
            return []

    def get_by_strategy(self, strategy: str) -> list[dict[str, Any]]:
        return [t for t in self.get_recent(n=100_000) if t.get("strategy") == strategy]

    def get_by_date_range(self, start: date, end: date) -> list[dict[str, Any]]:
        results = []
        for t in self.get_recent(n=100_000):
            ts = datetime.fromisoformat(t["timestamp"])
            if start <= ts.date() <= end:
                results.append(t)
        return results
