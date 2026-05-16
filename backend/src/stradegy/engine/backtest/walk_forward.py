from dataclasses import dataclass
from datetime import date
from typing import Callable

import numpy as np
import pandas as pd
import vectorbt as vbt
from loguru import logger

from stradegy.engine.strategy.base import BaseStrategy, Signal


@dataclass
class BacktestResult:
    strategy_name: str
    ticker: str
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    avg_trade_pnl: float
    total_trades: int
    equity_curve: pd.Series
    trades: pd.DataFrame
    train_start: date
    train_end: date
    test_start: date
    test_end: date


class WalkForwardBacktester:
    def __init__(
        self,
        train_size: int = 252 * 3,
        test_size: int = 252,
        min_train_size: int = 252,
        step_size: int = 63,
    ):
        self.train_size = train_size
        self.test_size = test_size
        self.min_train_size = min_train_size
        self.step_size = step_size

    def run(
        self,
        df: pd.DataFrame,
        ticker: str,
        strategy: BaseStrategy,
    ) -> list[BacktestResult]:
        if len(df) < self.min_train_size + self.test_size:
            logger.warning(f"Insufficient data for {ticker}: {len(df)} rows")
            return []

        results = []
        n = len(df)

        for start_idx in range(0, n - self.train_size - self.test_size + 1, self.step_size):
            train_end = start_idx + self.train_size
            test_end = train_end + self.test_size

            if test_end > n:
                break

            train_df = df.iloc[start_idx:train_end].copy()
            test_df = df.iloc[train_end:test_end].copy()

            logger.info(
                f"Walk-forward window: train={train_df.index[0].date()} to "
                f"{train_df.index[-1].date()}, test={test_df.index[0].date()} to "
                f"{test_df.index[-1].date()}"
            )

            result = self._run_single_window(
                train_df, test_df, ticker, strategy
            )
            if result:
                results.append(result)

        return results

    def _run_single_window(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        ticker: str,
        strategy: BaseStrategy,
    ) -> BacktestResult | None:
        try:
            signals = strategy.generate_signals(test_df, ticker)
            if not signals:
                return None

            entries = pd.Series(False, index=test_df.index)
            exits = pd.Series(False, index=test_df.index)

            for signal in signals:
                if signal.action == "buy":
                    entries.loc[signal.date] = True
                elif signal.action == "sell":
                    exits.loc[signal.date] = True

            if not entries.any():
                return None

            pf = vbt.Portfolio.from_signals(
                close=test_df["close"],
                entries=entries,
                exits=exits,
                freq="1d",
                init_cash=10000,
                fees=0.001,
                slippage=0.0005,
            )

            trades = pf.trades
            total_trades = len(trades) if trades is not None else 0
            win_rate = trades.win_rate() if total_trades > 0 else 0.0
            avg_pnl = trades.returns.mean() if total_trades > 0 else 0.0

            return BacktestResult(
                strategy_name=strategy.name,
                ticker=ticker,
                total_return=float(pf.total_return()),
                sharpe_ratio=float(pf.sharpe_ratio()) if not np.isnan(pf.sharpe_ratio()) else 0.0,
                sortino_ratio=float(pf.sortino_ratio()) if not np.isnan(pf.sortino_ratio()) else 0.0,
                calmar_ratio=float(pf.calmar_ratio()) if not np.isnan(pf.calmar_ratio()) else 0.0,
                max_drawdown=float(pf.max_drawdown()),
                win_rate=float(win_rate),
                avg_trade_pnl=float(avg_pnl),
                total_trades=total_trades,
                equity_curve=pf.value(),
                trades=(trades.to_pd() if hasattr(trades, "to_pd") else pd.DataFrame(getattr(trades, "records", {}))) if trades is not None else pd.DataFrame(),
                train_start=train_df.index[0].date(),
                train_end=train_df.index[-1].date(),
                test_start=test_df.index[0].date(),
                test_end=test_df.index[-1].date(),
            )

        except Exception as e:
            logger.error(f"Backtest error for {ticker}: {e}")
            return None

    def aggregate_results(self, results: list[BacktestResult]) -> dict:
        if not results:
            return {}

        returns = [r.total_return for r in results]
        sharpes = [r.sharpe_ratio for r in results]
        max_dd = [r.max_drawdown for r in results]
        win_rates = [r.win_rate for r in results]
        trades = [r.total_trades for r in results]

        return {
            "avg_total_return": np.mean(returns),
            "std_total_return": np.std(returns),
            "avg_sharpe": np.mean(sharpes),
            "avg_max_drawdown": np.mean(max_dd),
            "avg_win_rate": np.mean(win_rates),
            "total_trades": sum(trades),
            "windows_tested": len(results),
            "winning_windows": sum(1 for r in returns if r > 0),
        }
