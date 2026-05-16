import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from stradegy.db import async_session, init_db
from stradegy.engine.backtest.walk_forward import WalkForwardBacktester
from stradegy.engine.data.store import DataStore
from stradegy.engine.strategy.earnings_momentum import EarningsMomentumStrategy
from stradegy.engine.strategy.ensemble import EnsembleStrategy
from stradegy.engine.strategy.mean_reversion import MeanReversionStrategy
from stradegy.engine.strategy.momentum_breakout import MomentumBreakoutStrategy


async def main():
    await init_db()

    tickers = ["AAPL", "MSFT", "GOOGL"]
    strategies = {
        "MeanReversion": MeanReversionStrategy(),
        "MomentumBreakout": MomentumBreakoutStrategy(),
        "EarningsMomentum": EarningsMomentumStrategy(),
        "Ensemble": EnsembleStrategy(),
    }

    backtester = WalkForwardBacktester(
        train_size=252 * 3,
        test_size=252,
        step_size=63,
        min_train_size=252,
    )

    async with async_session() as session:
        store = DataStore(session)

        for ticker in tickers:
            print(f"\n{'='*60}")
            print(f"TICKER: {ticker}")
            print(f"{'='*60}")

            df = await store.get_ohlcv_dataframe(ticker, limit=5000)
            if df is None or len(df) < 1000:
                print(f"  Insufficient data: {len(df) if df is not None else 0} rows")
                continue

            print(f"  Data: {len(df)} rows from {df.index[0].date()} to {df.index[-1].date()}")

            for name, strategy in strategies.items():
                results = backtester.run(df.copy(), ticker, strategy)
                agg = backtester.aggregate_results(results)

                if agg:
                    print(f"\n  {name}:")
                    print(f"    Windows tested: {agg['windows_tested']}")
                    print(f"    Avg Return:     {agg['avg_total_return']:.2%}")
                    print(f"    Avg Sharpe:     {agg['avg_sharpe']:.2f}")
                    print(f"    Avg Max DD:     {agg['avg_max_drawdown']:.2%}")
                    print(f"    Avg Win Rate:   {agg['avg_win_rate']:.1%}")
                    print(f"    Total Trades:   {agg['total_trades']}")
                    print(f"    Winning Wnds:   {agg['winning_windows']}/{agg['windows_tested']}")
                else:
                    print(f"\n  {name}: No results")


if __name__ == "__main__":
    asyncio.run(main())
