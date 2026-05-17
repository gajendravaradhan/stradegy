import asyncio
from datetime import date, datetime, timezone

from loguru import logger

from stradegy.db import async_session
from stradegy.engine.research.discord_scanner import DiscordScanner
from stradegy.engine.research.gem_detector import GemDetector
from stradegy.engine.research.models import GemClassification, GemSignal
from stradegy.engine.research.news_scanner import NewsScanner
from stradegy.engine.research.reddit_scanner import RedditScanner
from stradegy.engine.research.sec_analyzer import SECAnalyzer
from stradegy.engine.research.discord_alerts import DiscordAlertManager
from stradegy.engine.research.telegram_alerts import TelegramAlertManager
from stradegy.engine.research.validator import Validator


class ResearchOrchestrator:
    def __init__(self):
        self.reddit = RedditScanner()
        self.discord = DiscordScanner()
        self.sec = SECAnalyzer()
        self.news = NewsScanner()
        self.gem_detector = GemDetector()
        self.validator = Validator()
        self.telegram = TelegramAlertManager()
        self.discord_alerts = DiscordAlertManager()

    async def run_market_open_scan(self):
        logger.info("Running market open research scan")
        tickers = await self._get_active_tickers()
        reddit_hot, discord_hot = await asyncio.gather(
            self._scan_reddit_and_group(),
            self._scan_discord_and_group(),
            return_exceptions=True,
        )
        if isinstance(reddit_hot, Exception):
            reddit_hot = {}
        if isinstance(discord_hot, Exception):
            discord_hot = {}
        hot_tickers = {**reddit_hot, **discord_hot}
        await self._run_full_pipeline(
            tickers, hot_tickers, reddit_data=reddit_hot, discord_data=discord_hot
        )

    async def run_close_scan(self):
        logger.info("Running market close SEC + News scan")
        tickers = await self._get_active_tickers()
        reddit_hot, discord_hot = await asyncio.gather(
            self._scan_reddit_and_group(),
            self._scan_discord_and_group(),
            return_exceptions=True,
        )
        if isinstance(reddit_hot, Exception):
            reddit_hot = {}
        if isinstance(discord_hot, Exception):
            discord_hot = {}
        hot_tickers = {**reddit_hot, **discord_hot}
        await self._run_full_pipeline(
            tickers, hot_tickers, reddit_data=reddit_hot, discord_data=discord_hot
        )

    async def run_incremental_scan(self):
        logger.info("Running incremental scan (hot tickers only)")
        reddit_hot, discord_hot = await asyncio.gather(
            self._scan_reddit_and_group(),
            self._scan_discord_and_group(),
            return_exceptions=True,
        )
        if isinstance(reddit_hot, Exception):
            reddit_hot = {}
        if isinstance(discord_hot, Exception):
            discord_hot = {}
        hot_tickers = {**reddit_hot, **discord_hot}
        if hot_tickers:
            await self._run_full_pipeline(
                list(hot_tickers.keys()), hot_tickers, reddit_data=reddit_hot, discord_data=discord_hot
            )
        else:
            logger.info("Incremental scan: no hot tickers found")

    async def run_weekend_deep(self):
        logger.info("Running weekend deep analysis")
        tickers = await self._get_active_tickers()
        reddit_hot, discord_hot = await asyncio.gather(
            self._scan_reddit_and_group(),
            self._scan_discord_and_group(),
            return_exceptions=True,
        )
        if isinstance(reddit_hot, Exception):
            reddit_hot = {}
        if isinstance(discord_hot, Exception):
            discord_hot = {}
        hot_tickers = {**reddit_hot, **discord_hot}
        await self._run_full_pipeline(
            tickers, hot_tickers, reddit_data=reddit_hot, discord_data=discord_hot, deep_mode=True
        )

    async def _scan_reddit_and_group(self) -> dict[str, list]:
        try:
            mentions = await self.reddit.scan_hot(limit=100)
            return self._group_mentions_by_ticker(mentions)
        except Exception as e:
            logger.error(f"Reddit scan failed: {e}")
            return {}

    async def _scan_discord_and_group(self) -> dict[str, list]:
        try:
            mentions = await self.discord.scan_hot(limit=100)
            return self._group_discord_mentions_by_ticker(mentions)
        except Exception as e:
            logger.error(f"Discord scan failed: {e}")
            return {}

    def _group_mentions_by_ticker(self, mentions: list) -> dict[str, list]:
        grouped = {}
        for m in mentions:
            ts = m.ticker_symbol.upper()
            if ts not in grouped:
                grouped[ts] = []
            grouped[ts].append({
                "sentiment_compound": m.sentiment_compound,
                "velocity_vs_avg": m.velocity_vs_avg,
                "upvote_ratio": m.upvote_ratio,
                "post_url": m.post_url,
            })
        return grouped

    def _group_discord_mentions_by_ticker(self, mentions: list) -> dict[str, list]:
        grouped = {}
        for m in mentions:
            ts = m.ticker_symbol.upper()
            if ts not in grouped:
                grouped[ts] = []
            grouped[ts].append({
                "sentiment_compound": m.sentiment_compound,
                "velocity_vs_avg": m.velocity_vs_avg,
                "num_reactions": m.num_reactions,
                "reply_count": m.reply_count,
                "message_url": m.message_url,
            })
        return grouped

    async def _run_full_pipeline(
        self,
        all_tickers: list[str],
        hot_tickers: dict[str, list],
        reddit_data: dict[str, list] | None = None,
        discord_data: dict[str, list] | None = None,
        deep_mode: bool = False,
    ):
        from stradegy.engine.data.store import DataStore
        from stradegy.engine.research.technical_filter import TechnicalFilter

        reddit_data = reddit_data or hot_tickers
        discord_data = discord_data or {}
        all_tickers_upper = [t.upper() for t in all_tickers]

        async with async_session() as session:
            store = DataStore(session)
            gems_found = []

            for ticker in all_tickers_upper:
                try:
                    reddit_mentions = reddit_data.get(ticker, [])
                    discord_mentions = discord_data.get(ticker, [])

                    technical = None
                    try:
                        tech_filter = TechnicalFilter(store)
                        technical = await tech_filter.analyze(ticker)
                    except Exception as e:
                        logger.warning(f"Technical filter failed for {ticker}: {e}")

                    sec_filing = None
                    news_sentiment = {}

                    if reddit_mentions or discord_mentions or deep_mode or (technical and technical.overall_pass):
                        try:
                            sec_filing = self.sec.analyze_10k(ticker)
                        except Exception as e:
                            logger.warning(f"SEC scan failed for {ticker}: {e}")

                        try:
                            news_sentiment = await self.news.aggregate_sentiment(ticker, limit=10)
                        except Exception as e:
                            logger.warning(f"News scan failed for {ticker}: {e}")

                    gem = self.gem_detector.detect(
                        ticker=ticker,
                        reddit_mentions=reddit_mentions,
                        discord_mentions=discord_mentions,
                        sec_filing=sec_filing,
                        news_sentiment=news_sentiment,
                        technical=technical,
                    )

                    if gem.classification in (GemClassification.STRONG, GemClassification.POTENTIAL):
                        self.validator.store = store
                        validation = await self.validator.validate(gem)
                        if validation.is_valid:
                            gems_found.append(gem)
                            await asyncio.gather(
                                self.telegram.send_gem_alert(gem),
                                self.discord_alerts.send_gem_alert(gem),
                                return_exceptions=True,
                            )
                            logger.info(
                                f"Valid gem alert sent for {ticker}: {gem.total_score}"
                            )
                        else:
                            logger.info(f"Gem rejected for {ticker}: {validation.failures}")
                    else:
                        logger.debug(f"No gem for {ticker}: {gem.total_score}")

                except Exception as e:
                    logger.error(f"Pipeline error for {ticker}: {e}")

            logger.info(
                f"Pipeline complete: {len(all_tickers)} tickers scanned, "
                f"{len(gems_found)} gems found"
            )

    async def _get_active_tickers(self) -> list[str]:
        from stradegy.engine.data.store import DataStore
        async with async_session() as session:
            store = DataStore(session)
            tickers = await store.get_active_tickers()
            return [t.symbol for t in tickers]
