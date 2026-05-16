import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from stradegy.db import async_session, init_db
from stradegy.engine.data.store import DataStore
from stradegy.engine.execution.alpaca_client import AlpacaClient
from stradegy.engine.risk.manager import RiskManager
from stradegy.engine.strategy.ensemble import EnsembleStrategy
from stradegy.engine.self_improvement.tracer import TradeTrace, TradeTracer
from loguru import logger


async def run_paper_trade_simulation(ticker: str = "AAPL"):
    logger.info(f"Starting paper trading simulation for {ticker}")
    await init_db()

    async with async_session() as session:
        store = DataStore(session)
        df = await store.get_ohlcv_dataframe(ticker)
        if df is None or len(df) < 100:
            logger.error(f"Insufficient data for {ticker}")
            return
        df = df.tail(300)

    from stradegy.engine.strategy.earnings_momentum import EarningsMomentumStrategy
    strategy = EarningsMomentumStrategy()
    risk_manager = RiskManager()
    tracer = TradeTracer()

    latest = df.iloc[-1]
    price = latest["close"]
    atr = df["close"].diff().abs().rolling(14).mean().iloc[-1]

    signals = strategy.generate_signals(df, ticker)
    if not signals:
        logger.info(f"No signals generated for {ticker} with {strategy.name}")
        return

    latest_signal = signals[-1]
    logger.info(f"Latest signal: {latest_signal.action} @ ${latest_signal.price:.2f} (confidence: {latest_signal.confidence:.2f})")

    equity = 25000.0
    position = risk_manager.calculate_position_size(equity=equity, atr=atr, price=price)

    logger.info(f"Risk assessment:")
    logger.info(f"  ATR: ${atr:.2f}")
    logger.info(f"  Stop distance: ${position['stop_distance']:.2f}")
    logger.info(f"  Shares: {position['shares']}")
    logger.info(f"  Position value: ${position['position_value']:.2f}")
    logger.info(f"  Stop loss: ${position['stop_loss']:.2f}")
    logger.info(f"  Risk amount: ${position['risk_amount']:.2f}")
    logger.info(f"  Risk %%: {position['risk_pct']:.2f}%")

    trace = TradeTrace(
        trade_id=f"sim-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        timestamp=datetime.now(),
        ticker=ticker,
        action=latest_signal.action,
        price=price,
        shares=position["shares"],
        strategy=strategy.name,
        signal_confidence=latest_signal.confidence,
        expected_outcome="paper_trade_simulation",
    )
    tracer.append(trace)
    logger.info(f"Trade trace logged to {tracer.log_file}")

    try:
        client = AlpacaClient()
        account = await client.get_account()
        if account:
            logger.info(f"Alpaca account: equity=${account.get('equity', 0):.2f}")
        else:
            logger.warning("Alpaca account not available (paper trading mode with no credentials)")
    except Exception as e:
        logger.warning(f"Alpaca client not available: {e}")

    dd_check = risk_manager.check_drawdown(equity=equity, peak_equity=equity)
    logger.info(f"Drawdown check: safe={dd_check['is_safe']}, kill_switch={dd_check['kill_switch']}")

    emergency = risk_manager.emergency_check(
        equity=equity,
        peak_equity=equity,
        pdt_data=risk_manager.check_pdt([]),
        correlation_warnings=[],
    )
    logger.info(f"Emergency status: is_emergency={emergency['is_emergency']}, should_halt={emergency['should_halt_trading']}")

    logger.info("Paper trading simulation complete")


if __name__ == "__main__":
    asyncio.run(run_paper_trade_simulation("AAPL"))
