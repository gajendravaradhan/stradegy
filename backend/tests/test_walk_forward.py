import numpy as np
import pandas as pd
import pytest

from stradegy.engine.backtest.walk_forward import BacktestResult, WalkForwardBacktester
from stradegy.engine.strategy.base import BaseStrategy, Signal


class MockStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("MockStrategy")

    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        signals = []
        for i in range(1, len(df)):
            idx = df.index[i]
            price = df["close"].iloc[i]
            if i % 10 == 0:
                signals.append(
                    Signal(ticker=ticker, date=idx.date(), action="buy", price=price, confidence=0.8)
                )
            elif i % 10 == 5:
                signals.append(
                    Signal(ticker=ticker, date=idx.date(), action="sell", price=price, confidence=0.8)
                )
        return signals


class NoSignalStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("NoSignal")

    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        return []


def make_ohlcv(n: int, start_date: str = "2020-01-01") -> pd.DataFrame:
    rng = pd.date_range(start=start_date, periods=n, freq="D")
    np.random.seed(42)
    base = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame(
        {
            "open": base + np.random.randn(n) * 0.2,
            "high": base + np.abs(np.random.randn(n)) * 0.5,
            "low": base - np.abs(np.random.randn(n)) * 0.5,
            "close": base + np.random.randn(n) * 0.3,
            "volume": np.random.randint(1_000_000, 10_000_000, n),
        },
        index=rng,
    )
    return df


def test_walk_forward_basic():
    df = make_ohlcv(800)
    strategy = MockStrategy()
    bt = WalkForwardBacktester(train_size=200, test_size=100, step_size=100, min_train_size=100)
    results = bt.run(df, "TEST", strategy)

    assert isinstance(results, list)
    assert len(results) > 0
    for r in results:
        assert isinstance(r, BacktestResult)
        assert r.strategy_name == "MockStrategy"
        assert r.ticker == "TEST"
        assert isinstance(r.total_return, float)
        assert isinstance(r.sharpe_ratio, float)
        assert isinstance(r.max_drawdown, float)
        assert isinstance(r.total_trades, int)
        assert r.train_start < r.train_end
        assert r.test_start < r.test_end
        assert r.train_end <= r.test_start


def test_walk_forward_insufficient_data():
    df = make_ohlcv(50)
    strategy = MockStrategy()
    bt = WalkForwardBacktester(train_size=200, test_size=100, step_size=100, min_train_size=100)
    results = bt.run(df, "TEST", strategy)
    assert results == []


def test_walk_forward_no_signals():
    df = make_ohlcv(800)
    strategy = NoSignalStrategy()
    bt = WalkForwardBacktester(train_size=200, test_size=100, step_size=100, min_train_size=100)
    results = bt.run(df, "TEST", strategy)
    assert results == []


def test_aggregate_results():
    bt = WalkForwardBacktester()
    results = [
        BacktestResult(
            strategy_name="S", ticker="A", total_return=0.10, sharpe_ratio=1.0,
            sortino_ratio=1.2, calmar_ratio=0.8, max_drawdown=0.05,
            win_rate=0.6, avg_trade_pnl=0.01, total_trades=5,
            equity_curve=pd.Series(), trades=pd.DataFrame(),
            train_start=pd.Timestamp("2020-01-01").date(),
            train_end=pd.Timestamp("2020-06-01").date(),
            test_start=pd.Timestamp("2020-06-02").date(),
            test_end=pd.Timestamp("2020-12-01").date(),
        ),
        BacktestResult(
            strategy_name="S", ticker="A", total_return=-0.05, sharpe_ratio=-0.5,
            sortino_ratio=-0.4, calmar_ratio=-0.3, max_drawdown=0.10,
            win_rate=0.4, avg_trade_pnl=-0.005, total_trades=3,
            equity_curve=pd.Series(), trades=pd.DataFrame(),
            train_start=pd.Timestamp("2020-03-01").date(),
            train_end=pd.Timestamp("2020-09-01").date(),
            test_start=pd.Timestamp("2020-09-02").date(),
            test_end=pd.Timestamp("2021-03-01").date(),
        ),
    ]
    agg = bt.aggregate_results(results)
    assert agg["avg_total_return"] == pytest.approx(0.025, abs=0.01)
    assert agg["avg_sharpe"] == pytest.approx(0.25, abs=0.01)
    assert agg["avg_max_drawdown"] == pytest.approx(0.075, abs=0.01)
    assert agg["avg_win_rate"] == pytest.approx(0.5, abs=0.01)
    assert agg["total_trades"] == 8
    assert agg["windows_tested"] == 2
    assert agg["winning_windows"] == 1


def test_aggregate_empty():
    bt = WalkForwardBacktester()
    agg = bt.aggregate_results([])
    assert agg == {}
