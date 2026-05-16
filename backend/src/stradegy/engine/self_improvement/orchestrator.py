from datetime import date, datetime, timedelta
from typing import Any

from loguru import logger

from stradegy.engine.backtest.walk_forward import WalkForwardBacktester
from stradegy.engine.data.store import DataStore
from stradegy.engine.self_improvement.analyzer import TraceAnalyzer
from stradegy.engine.self_improvement.metrics import BaselineSnapshot, MetricsBaseline
from stradegy.engine.self_improvement.ratchet import RatchetLoop
from stradegy.engine.self_improvement.skillbook import Skillbook
from stradegy.engine.self_improvement.tracer import TradeTracer
from stradegy.engine.self_improvement.versioning import VersionManager
from stradegy.engine.strategy.ensemble import EnsembleStrategy


class SelfImprovementOrchestrator:
    def __init__(self):
        self.tracer = TradeTracer()
        self.analyzer = TraceAnalyzer(self.tracer)
        self.metrics = MetricsBaseline()
        self.skillbook = Skillbook()
        self.version_manager = VersionManager()
        self.ratchet = RatchetLoop(self.metrics, self.skillbook, self.version_manager)
        self.backtester = WalkForwardBacktester(train_size=252, test_size=63, step_size=63, min_train_size=126)

    async def run_weekly_cycle(self, store: DataStore | None = None) -> dict[str, Any]:
        logger.info("Starting weekly self-improvement cycle")

        recommendations = self.analyzer.generate_recommendations()
        if not recommendations:
            logger.info("No recommendations generated. Cycle complete.")
            return {"action": "none", "reason": "no recommendations"}

        results = []
        for rec in recommendations:
            if rec["type"] == "reduce_weight":
                result = await self._adjust_strategy_weight(rec["target"], store)
                results.append(result)

        return {"action": "cycle_complete", "results": results}

    async def _adjust_strategy_weight(self, strategy_name: str, store: DataStore | None = None) -> dict[str, Any]:
        logger.info(f"Adjusting weight for {strategy_name}")

        latest = self.version_manager.get_latest(strategy_name)
        current_params = latest.params if latest else {"weight": 0.33}
        new_params = dict(current_params)
        new_params["weight"] = max(0.1, current_params.get("weight", 0.33) - 0.05)

        proposal = self.ratchet.propose_change(strategy_name, new_params)

        if store is not None:
            backtest_metrics = await self._run_quick_backtest(store, strategy_name, new_params)
        else:
            backtest_metrics = {"sharpe": 0.0, "max_drawdown": 0.0, "win_rate": 0.0, "total_return": 0.0, "total_trades": 0}

        evaluation = self.ratchet.evaluate_change(proposal["version_id"], backtest_metrics)
        decision = self.ratchet.keep_or_revert(evaluation)

        return {
            "strategy": strategy_name,
            "version_id": proposal["version_id"],
            "params": new_params,
            "evaluation": evaluation,
            "decision": decision,
        }

    async def _run_quick_backtest(self, store: DataStore, strategy_name: str, params: dict[str, Any]) -> dict[str, float]:
        try:
            from stradegy.engine.strategy.mean_reversion import MeanReversionStrategy
            from stradegy.engine.strategy.momentum_breakout import MomentumBreakoutStrategy
            from stradegy.engine.strategy.earnings_momentum import EarningsMomentumStrategy

            strategy_map = {
                "MeanReversion": MeanReversionStrategy,
                "MomentumBreakout": MomentumBreakoutStrategy,
                "EarningsMomentum": EarningsMomentumStrategy,
            }
            strategy_cls = strategy_map.get(strategy_name, MeanReversionStrategy)
            strategy = strategy_cls(**params)

            sample_tickers = ["AAPL", "MSFT", "GOOGL"]
            combined_metrics: dict[str, list[float]] = {"sharpe": [], "max_drawdown": [], "win_rate": [], "total_return": [], "total_trades": []}

            for ticker in sample_tickers:
                df = await store.get_ohlcv_dataframe(ticker, limit=800)
                if df is None or len(df) < 300:
                    continue
                results = self.backtester.run(df, ticker, strategy)
                if results:
                    agg = self.backtester.aggregate_results(results)
                    if agg:
                        combined_metrics["sharpe"].append(agg.get("avg_sharpe", 0))
                        combined_metrics["max_drawdown"].append(abs(agg.get("avg_max_drawdown", 0)))
                        combined_metrics["win_rate"].append(agg.get("avg_win_rate", 0))
                        combined_metrics["total_return"].append(agg.get("avg_total_return", 0))
                        combined_metrics["total_trades"].append(agg.get("total_trades", 0))

            return {
                "sharpe": sum(combined_metrics["sharpe"]) / len(combined_metrics["sharpe"]) if combined_metrics["sharpe"] else 0.0,
                "max_drawdown": sum(combined_metrics["max_drawdown"]) / len(combined_metrics["max_drawdown"]) if combined_metrics["max_drawdown"] else 0.0,
                "win_rate": sum(combined_metrics["win_rate"]) / len(combined_metrics["win_rate"]) if combined_metrics["win_rate"] else 0.0,
                "total_return": sum(combined_metrics["total_return"]) / len(combined_metrics["total_return"]) if combined_metrics["total_return"] else 0.0,
                "total_trades": sum(combined_metrics["total_trades"]) / len(combined_metrics["total_trades"]) if combined_metrics["total_trades"] else 0.0,
            }
        except Exception as e:
            logger.error(f"Quick backtest failed for {strategy_name}: {e}")
            return {"sharpe": 0.0, "max_drawdown": 0.0, "win_rate": 0.0, "total_return": 0.0, "total_trades": 0}

    def record_baseline(self, metrics: dict[str, float]) -> None:
        snap = BaselineSnapshot(
            date=datetime.now().strftime("%Y-%m-%d"),
            sharpe=metrics.get("sharpe", 0),
            sortino=metrics.get("sortino", 0),
            calmar=metrics.get("calmar", 0),
            max_drawdown=metrics.get("max_drawdown", 0),
            win_rate=metrics.get("win_rate", 0),
            total_trades=int(metrics.get("total_trades", 0)),
            total_return=metrics.get("total_return", 0),
        )
        self.metrics.record(snap)
