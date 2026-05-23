from datetime import datetime, timezone
from typing import Any

from loguru import logger

from stradegy.config import settings
from stradegy.db import async_session
from stradegy.engine.data.store import DataStore
from stradegy.engine.execution.alpaca_client import AlpacaClient
from stradegy.engine.research.gem_detector import GemDetector
from stradegy.engine.research.technical_filter import TechnicalFilter


class PaperTradeLogger:
    def __init__(self):
        self.gem_detector = GemDetector()

    async def log_signals(self, tickers: list[str]) -> dict[str, Any]:
        logged = []
        async with async_session() as session:
            store = DataStore(session)
            for ticker in tickers[:20]:
                try:
                    tech_filter = TechnicalFilter(store)
                    technical = await tech_filter.analyze(ticker)
                    if not technical or not technical.overall_pass:
                        continue

                    gem = self.gem_detector.detect(
                        ticker=ticker,
                        reddit_mentions=[],
                        discord_mentions=[],
                        stocktwits_mentions=[],
                        insider_signals=[],
                        trends=None,
                        earnings=[],
                        sec_filing=None,
                        news_sentiment={},
                        technical=technical,
                    )

                    if gem.classification.value in ("strong_gem", "potential_gem"):
                        paper_trade = {
                            "ticker": ticker,
                            "signal_time": datetime.now(timezone.utc).isoformat(),
                            "action": "buy",
                            "score": gem.total_score,
                            "classification": gem.classification.value,
                            "technical_score": gem.technical_score,
                            "price": technical.price,
                            "status": "paper",
                        }
                        logged.append(paper_trade)
                        logger.info(f"Paper trade logged: {ticker} @ {technical.price:.2f} (score: {gem.total_score})")
                except Exception as e:
                    logger.debug(f"Paper trade error for {ticker}: {e}")

        return {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "trades_logged": len(logged),
            "trades": logged,
        }
