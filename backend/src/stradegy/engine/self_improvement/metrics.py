from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import json
from loguru import logger

from stradegy.config import settings


@dataclass
class BaselineSnapshot:
    date: str
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    total_return: float


class MetricsBaseline:
    def __init__(self, path: Path | None = None):
        self.path = path or (settings.eval_dir / "baseline.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshots: list[BaselineSnapshot] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        self._snapshots.append(BaselineSnapshot(**obj))
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")

    def _save(self) -> None:
        try:
            with self.path.open("w") as f:
                for snap in self._snapshots:
                    f.write(json.dumps(asdict(snap)) + "\n")
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")

    def record(self, snapshot: BaselineSnapshot) -> None:
        self._snapshots.append(snapshot)
        self._save()

    def latest(self) -> BaselineSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def compare(self, current: dict[str, float]) -> dict[str, Any]:
        baseline = self.latest()
        if not baseline:
            return {"is_improved": True, "differences": {}}

        diffs = {}
        for key in ["sharpe", "sortino", "calmar", "win_rate", "total_return"]:
            base_val = getattr(baseline, key, 0)
            curr_val = current.get(key, 0)
            diffs[key] = {
                "baseline": base_val,
                "current": curr_val,
                "delta": curr_val - base_val,
            }

        is_improved = sum(1 for d in diffs.values() if d["delta"] > 0) >= len(diffs) // 2
        return {"is_improved": is_improved, "differences": diffs}

    def is_regression(self, current: dict[str, float], sharpe_threshold: float = 0.2, drawdown_threshold: float = 0.05) -> bool:
        baseline = self.latest()
        if not baseline:
            return False
        sharpe_drop = baseline.sharpe - current.get("sharpe", baseline.sharpe)
        dd_increase = current.get("max_drawdown", baseline.max_drawdown) - baseline.max_drawdown
        return sharpe_drop > sharpe_threshold or dd_increase > drawdown_threshold
