from datetime import datetime
from typing import Any

from loguru import logger

from stradegy.engine.self_improvement.metrics import BaselineSnapshot, MetricsBaseline
from stradegy.engine.self_improvement.skillbook import Skill, Skillbook
from stradegy.engine.self_improvement.versioning import StrategyVersion, VersionManager


class RatchetLoop:
    def __init__(
        self,
        baseline: MetricsBaseline | None = None,
        skillbook: Skillbook | None = None,
        version_manager: VersionManager | None = None,
    ):
        self.baseline = baseline or MetricsBaseline()
        self.skillbook = skillbook or Skillbook()
        self.version_manager = version_manager or VersionManager()

    def propose_change(self, strategy_name: str, new_params: dict[str, Any]) -> dict[str, Any]:
        latest = self.version_manager.get_latest(strategy_name)
        version_id = f"{strategy_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        version = StrategyVersion(
            version_id=version_id,
            timestamp=datetime.now().isoformat(),
            strategy_name=strategy_name,
            params=new_params,
            metrics={},
            parent_version=latest.version_id if latest else None,
        )
        self.version_manager.save(version)
        return {"version_id": version_id, "params": new_params}

    def evaluate_change(self, version_id: str, backtest_metrics: dict[str, float]) -> dict[str, Any]:
        for v in self.version_manager._versions:
            if v.version_id == version_id:
                v.metrics = backtest_metrics
                self.version_manager._save()
                break

        comparison = self.baseline.compare(backtest_metrics)
        is_regression = self.baseline.is_regression(backtest_metrics)

        return {
            "version_id": version_id,
            "metrics": backtest_metrics,
            "improved": comparison["is_improved"],
            "regression": is_regression,
            "differences": comparison["differences"],
        }

    def keep_or_revert(self, evaluation: dict[str, Any]) -> dict[str, Any]:
        version_id = evaluation["version_id"]
        if evaluation["regression"]:
            logger.warning(f"Version {version_id} regressed. Reverting to previous params.")
            return {"action": "revert", "version_id": version_id, "reason": "regression"}

        if evaluation["improved"]:
            snap = BaselineSnapshot(
                date=datetime.now().strftime("%Y-%m-%d"),
                sharpe=evaluation["metrics"].get("sharpe", 0),
                sortino=evaluation["metrics"].get("sortino", 0),
                calmar=evaluation["metrics"].get("calmar", 0),
                max_drawdown=evaluation["metrics"].get("max_drawdown", 0),
                win_rate=evaluation["metrics"].get("win_rate", 0),
                total_trades=int(evaluation["metrics"].get("total_trades", 0)),
                total_return=evaluation["metrics"].get("total_return", 0),
            )
            self.baseline.record(snap)
            logger.info(f"Version {version_id} improved. New baseline recorded.")
            return {"action": "keep", "version_id": version_id, "reason": "improved"}

        logger.info(f"Version {version_id} neutral. Keeping but no baseline update.")
        return {"action": "keep", "version_id": version_id, "reason": "neutral"}
