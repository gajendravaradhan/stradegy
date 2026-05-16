from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
from loguru import logger

from stradegy.engine.self_improvement.analyzer import TraceAnalyzer
from stradegy.engine.self_improvement.metrics import BaselineSnapshot, MetricsBaseline
from stradegy.engine.self_improvement.tracer import TradeTracer
from stradegy.engine.self_improvement.versioning import VersionManager


class StrategyReviewer:
    def __init__(self):
        self.tracer = TradeTracer()
        self.analyzer = TraceAnalyzer(self.tracer)
        self.metrics = MetricsBaseline()
        self.version_manager = VersionManager()

    def review_monthly(self) -> dict[str, Any]:
        logger.info("Running monthly strategy review")

        stats = self.analyzer.analyze_by_strategy(days=30)
        if not stats:
            logger.info("No trades found in the last 30 days")
            return {"period": "monthly", "has_data": False, "strategies": []}

        strategies = []
        for name, metrics in stats.items():
            win_rate = metrics["win_rate"]
            avg_pnl = metrics["avg_pnl"]
            total_pnl = metrics["total_pnl"]
            total_trades = metrics["total_trades"]

            pnls = self._get_pnls(name, days=30)
            sharpe = self._calculate_sharpe(pnls)
            max_dd = self._calculate_max_drawdown(pnls)

            status = self._classify_performance(win_rate, sharpe, max_dd)

            strategies.append({
                "name": name,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "avg_pnl": avg_pnl,
                "total_pnl": total_pnl,
                "sharpe": sharpe,
                "max_drawdown": max_dd,
                "status": status,
            })

        recommendations = self._generate_recommendations(strategies)

        return {
            "period": "monthly",
            "has_data": True,
            "review_date": datetime.now().isoformat(),
            "strategies": strategies,
            "recommendations": recommendations,
        }

    def review_quarterly(self) -> dict[str, Any]:
        logger.info("Running quarterly strategy review")

        stats = self.analyzer.analyze_by_strategy(days=90)
        if not stats:
            logger.info("No trades found in the last 90 days")
            return {"period": "quarterly", "has_data": False, "strategies": []}

        strategies = []
        for name, metrics in stats.items():
            win_rate = metrics["win_rate"]
            avg_pnl = metrics["avg_pnl"]
            total_pnl = metrics["total_pnl"]
            total_trades = metrics["total_trades"]

            pnls = self._get_pnls(name, days=90)
            sharpe = self._calculate_sharpe(pnls)
            max_dd = self._calculate_max_drawdown(pnls)

            status = self._classify_performance(
                win_rate, sharpe, max_dd, strict=True
            )

            strategies.append({
                "name": name,
                "total_trades": total_trades,
                "win_rate": win_rate,
                "avg_pnl": avg_pnl,
                "total_pnl": total_pnl,
                "sharpe": sharpe,
                "max_drawdown": max_dd,
                "status": status,
            })

        recommendations = self._generate_recommendations(strategies, quarterly=True)
        midterm_goals = self._generate_midterm_goals(strategies)

        return {
            "period": "quarterly",
            "has_data": True,
            "review_date": datetime.now().isoformat(),
            "strategies": strategies,
            "recommendations": recommendations,
            "midterm_goals": midterm_goals,
        }

    def _get_pnls(self, strategy_name: str, days: int) -> list[float]:
        cutoff = date.today() - timedelta(days=days)
        trades = self.tracer.get_by_date_range(cutoff, date.today())
        return [
            t["pnl"] for t in trades
            if t.get("strategy") == strategy_name and t.get("pnl") is not None
        ]

    def _calculate_sharpe(self, pnls: list[float], risk_free_rate: float = 0.0) -> float:
        if not pnls or len(pnls) < 2:
            return 0.0
        returns = np.array(pnls)
        mean_return = np.mean(returns) - risk_free_rate
        std_return = np.std(returns, ddof=1)
        if std_return == 0:
            return 0.0
        return float(mean_return / std_return)

    def _calculate_max_drawdown(self, pnls: list[float]) -> float:
        if not pnls:
            return 0.0
        cumulative = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = running_max - cumulative
        max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
        return float(max_dd)

    def _classify_performance(
        self,
        win_rate: float,
        sharpe: float,
        max_drawdown: float,
        strict: bool = False,
    ) -> str:
        if strict:
            if win_rate >= 0.55 and sharpe >= 1.0 and max_drawdown < 500:
                return "strong"
            elif win_rate >= 0.45 and sharpe >= 0.5 and max_drawdown < 1000:
                return "acceptable"
            else:
                return "weak"
        else:
            if win_rate >= 0.50 and sharpe >= 0.8 and max_drawdown < 500:
                return "strong"
            elif win_rate >= 0.40 and sharpe >= 0.3 and max_drawdown < 1000:
                return "acceptable"
            else:
                return "weak"

    def _generate_recommendations(
        self, strategies: list[dict[str, Any]], quarterly: bool = False
    ) -> list[dict[str, Any]]:
        recommendations = []

        for s in strategies:
            if s["status"] == "weak":
                severity = "high" if s["win_rate"] < 0.35 else "medium"
                recommendations.append({
                    "type": "reduce_weight",
                    "target": s["name"],
                    "reason": (
                        f"Weak performance: win rate {s['win_rate']:.1%}, "
                        f"sharpe {s['sharpe']:.2f}, max drawdown ${s['max_drawdown']:.2f}"
                    ),
                    "severity": severity,
                    "suggested_action": (
                        f"Reduce {s['name']} weight by 0.05-0.10 and "
                        f"increase capital allocation to stronger strategies"
                    ),
                })
            elif s["status"] == "acceptable" and quarterly:
                recommendations.append({
                    "type": "tune_params",
                    "target": s["name"],
                    "reason": (
                        f"Acceptable but not optimal: win rate {s['win_rate']:.1%}, "
                        f"sharpe {s['sharpe']:.2f}"
                    ),
                    "severity": "low",
                    "suggested_action": (
                        f"Run parameter optimization for {s['name']} to improve edge"
                    ),
                })

        if not recommendations and all(s["status"] == "strong" for s in strategies):
            recommendations.append({
                "type": "increase_risk",
                "target": "portfolio",
                "reason": "All strategies performing strongly",
                "severity": "low",
                "suggested_action": "Consider increasing risk_per_trade by 0.005",
            })

        return recommendations

    def _generate_midterm_goals(
        self, strategies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        goals = []

        avg_win_rate = np.mean([s["win_rate"] for s in strategies]) if strategies else 0
        avg_sharpe = np.mean([s["sharpe"] for s in strategies]) if strategies else 0

        if avg_win_rate < 0.50:
            goals.append({
                "goal": "Improve ensemble win rate to 50%+",
                "current": f"{avg_win_rate:.1%}",
                "target": "50%",
                "tactic": "Focus on entry signal quality; add volume confirmation filter",
            })

        if avg_sharpe < 1.0:
            goals.append({
                "goal": "Achieve Sharpe ratio of 1.0+",
                "current": f"{avg_sharpe:.2f}",
                "target": "1.00",
                "tactic": "Tighten stop losses; reduce holding periods for losers",
            })

        goals.append({
            "goal": "Maintain max drawdown below $1,000",
            "current": "varies by strategy",
            "target": "<$1,000",
            "tactic": "Dynamic position sizing based on recent volatility",
        })

        return goals

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
