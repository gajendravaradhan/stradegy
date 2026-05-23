import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from stradegy.db import async_session
from stradegy.engine.backtest.walk_forward import WalkForwardBacktester
from stradegy.engine.data.store import DataStore


class OvernightBacktestRunner:
    def __init__(self):
        self.backtester = WalkForwardBacktester(
            train_size=252, test_size=63, step_size=63, min_train_size=126
        )

    async def run_nightly(self) -> dict[str, Any]:
        results = {}
        async with async_session() as session:
            store = DataStore(session)
            tickers = await store.get_active_tickers()
            test_tickers = [t.symbol for t in tickers[:5]]
            strategies = ["mean_reversion", "momentum_breakout", "earnings_momentum"]

            for ticker in test_tickers:
                try:
                    df = await store.get_ohlcv_dataframe(ticker, limit=500)
                    if df is None or len(df) < 200:
                        continue
                    for strategy in strategies:
                        try:
                            bt_results = self.backtester.run(df, ticker, strategy)
                            agg = self.backtester.aggregate_results(bt_results)
                            key = f"{ticker}_{strategy}"
                            results[key] = {
                                "sharpe": agg.get("sharpe", 0),
                                "max_drawdown": agg.get("max_drawdown", 0),
                                "win_rate": agg.get("win_rate", 0),
                                "total_return": agg.get("total_return", 0),
                                "total_trades": agg.get("total_trades", 0),
                            }
                        except Exception as e:
                            logger.debug(f"Backtest error {ticker}/{strategy}: {e}")
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Nightly backtest error for {ticker}: {e}")

        logger.info(f"Overnight backtest complete: {len(results)} strategy-ticker combinations")
        return {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
        }
