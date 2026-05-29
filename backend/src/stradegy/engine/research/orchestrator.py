import asyncio
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from loguru import logger
from sqlalchemy import select

from stradegy.config import settings
from stradegy.db import async_session
from stradegy.engine.data.store import DataStore
from stradegy.engine.research.discord_scanner import DiscordScanner
from stradegy.engine.research.earnings_scanner import EarningsScanner
from stradegy.engine.research.gem_detector import GemDetector
from stradegy.engine.research.models import GemClassification, GemSignal
from stradegy.engine.research.db import GemSignalRecord
from stradegy.engine.research.news_scanner import NewsScanner
from stradegy.engine.research.openinsider_scraper import OpenInsiderScraper
from stradegy.engine.research.reddit_scanner import RedditScanner
from stradegy.engine.research.sec_analyzer import SECAnalyzer
from stradegy.engine.research.stocktwits_scanner import StockTwitsScanner
from stradegy.engine.research.trends_scanner import GoogleTrendsScanner
from stradegy.engine.research.alpaca_news_scanner import AlpacaNewsScanner
from stradegy.engine.research.hackernews_scanner import HackerNewsScanner
from stradegy.engine.research.telegram_scanner import TelegramScanner
from stradegy.engine.research.bluesky_scanner import BlueskyScanner
from stradegy.engine.research.youtube_scanner import YouTubeScanner
from stradegy.engine.research.fred_scanner import FredScanner
from stradegy.engine.research.fear_greed_scanner import FearGreedScanner
from stradegy.engine.research.options_scanner import OptionsScanner
from stradegy.engine.research.twelve_data_scanner import TwelveDataScanner
from stradegy.engine.research.fmp_analyst_scanner import FMPAnalystScanner
from stradegy.engine.research.finra_scanner import FINRAScanner
from stradegy.engine.research.keyvex_scanner import KeyVexScanner
from stradegy.engine.research.adanos_scanner import AdanosScanner
from stradegy.engine.alerts.whatsapp_alerts import WhatsAppAlertManager
from stradegy.engine.research.discord_alerts import DiscordAlertManager
from stradegy.engine.research.telegram_alerts import TelegramAlertManager
from stradegy.engine.research.validator import Validator


TICKER_PATTERN = re.compile(r"\b[A-Z]{1,5}\b")


class ResearchOrchestrator:
    """Discovers tickers from Reddit/Discord/News/SEC, then scores candidates."""

    def __init__(self):
        self.reddit = RedditScanner()
        self.discord = DiscordScanner()
        self.stocktwits = StockTwitsScanner()
        self.insider = OpenInsiderScraper()
        self.trends = GoogleTrendsScanner()
        self.earnings = EarningsScanner()
        self.sec = SECAnalyzer()
        self.news = NewsScanner()
        self.alpaca_news = AlpacaNewsScanner()
        self.hackernews = HackerNewsScanner()
        self.telegram_scanner = TelegramScanner()
        self.bluesky = BlueskyScanner()
        self.youtube = YouTubeScanner()
        self.fred = FredScanner()
        self.fear_greed = FearGreedScanner()
        self.options = OptionsScanner()
        self.twelve_data = TwelveDataScanner()
        self.fmp = FMPAnalystScanner()
        self.finra = FINRAScanner()
        self.keyvex = KeyVexScanner()
        self.adanos = AdanosScanner()
        self.gem_detector = GemDetector()
        self.validator = Validator()
        self.telegram = TelegramAlertManager()
        self.discord_alerts = DiscordAlertManager()
        self.whatsapp = WhatsAppAlertManager()

    async def run_market_open_scan(self):
        logger.info("Running market open research scan (discovery mode)")
        candidates, reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data = await self._discover_candidates()
        await self._run_full_pipeline(candidates, reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data)

    async def run_close_scan(self):
        logger.info("Running market close SEC + News scan (discovery mode)")
        candidates, reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data = await self._discover_candidates()
        await self._run_full_pipeline(candidates, reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data)

    async def run_incremental_scan(self):
        logger.info("Running incremental scan (discovery mode)")
        candidates, reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data = await self._discover_candidates(incremental=True)
        if candidates:
            await self._run_full_pipeline(candidates, reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data)
        else:
            logger.info("Incremental scan: no candidates discovered")

    async def run_weekend_deep(self):
        logger.info("Running weekend deep analysis (discovery mode)")
        candidates, reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data = await self._discover_candidates(deep_mode=True)
        await self._run_full_pipeline(candidates, reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data, deep_mode=True)

    async def _discover_candidates(
        self, incremental: bool = False, deep_mode: bool = False
    ):
        logger.info("Discovering candidates from all sources...")

        reddit_mentions, discord_mentions, stocktwits_mentions, insider_signals, earnings_signals, base_tickers, alpaca_news_mentions, hackernews_mentions, telegram_mentions, bluesky_mentions, youtube_mentions = await asyncio.gather(
            self._safe_scan(self.reddit.scan_hot, limit=100),
            self._safe_scan(self.discord.scan_hot, limit=100),
            self._safe_scan(self.stocktwits.scan_hot, limit=50),
            self._safe_scan(self.insider.scan_recent, days=7),
            self._safe_scan(self.earnings.scan_upcoming),
            self._get_active_tickers(),
            self._safe_scan(self.alpaca_news.scan_hot, limit=50),
            self._safe_scan(self.hackernews.scan_hot, limit=50),
            self._safe_scan(self.telegram_scanner.scan_hot, limit=50),
            self._safe_scan(self.bluesky.scan_hot, limit=50),
            self._safe_scan(self.youtube.scan_hot, limit=30),
            return_exceptions=True,
        )

        if isinstance(reddit_mentions, Exception):
            logger.error(f"Reddit discovery failed: {reddit_mentions}")
            reddit_mentions = []
        if isinstance(discord_mentions, Exception):
            logger.error(f"Discord discovery failed: {discord_mentions}")
            discord_mentions = []
        if isinstance(stocktwits_mentions, Exception):
            logger.error(f"StockTwits discovery failed: {stocktwits_mentions}")
            stocktwits_mentions = []
        if isinstance(insider_signals, Exception):
            logger.error(f"Insider discovery failed: {insider_signals}")
            insider_signals = []
        if isinstance(earnings_signals, Exception):
            logger.error(f"Earnings discovery failed: {earnings_signals}")
            earnings_signals = []
        if isinstance(base_tickers, Exception):
            logger.error(f"Base ticker fetch failed: {base_tickers}")
            base_tickers = []

        if isinstance(alpaca_news_mentions, Exception):
            logger.error(f"Alpaca News discovery failed: {alpaca_news_mentions}")
            alpaca_news_mentions = []
        if isinstance(hackernews_mentions, Exception):
            logger.error(f"HackerNews discovery failed: {hackernews_mentions}")
            hackernews_mentions = []
        if isinstance(telegram_mentions, Exception):
            logger.error(f"Telegram discovery failed: {telegram_mentions}")
            telegram_mentions = []
        if isinstance(bluesky_mentions, Exception):
            logger.error(f"Bluesky discovery failed: {bluesky_mentions}")
            bluesky_mentions = []
        if isinstance(youtube_mentions, Exception):
            logger.error(f"YouTube discovery failed: {youtube_mentions}")
            youtube_mentions = []

        reddit_data = self._mentions_to_dict(reddit_mentions)
        discord_data = self._mentions_to_dict(discord_mentions)
        stocktwits_data = self._mentions_to_dict(stocktwits_mentions)
        insider_data = self._group_insider_by_ticker(insider_signals)
        earnings_data = self._group_earnings_by_ticker(earnings_signals)
        alpaca_news_data = self._mentions_to_dict(alpaca_news_mentions)
        hackernews_data = self._mentions_to_dict(hackernews_mentions)
        telegram_data = self._mentions_to_dict(telegram_mentions)
        bluesky_data = self._mentions_to_dict(bluesky_mentions)
        youtube_data = self._mentions_to_dict(youtube_mentions)

        reddit_tickers = set(reddit_data.keys())
        discord_tickers = set(discord_data.keys())
        stocktwits_tickers = set(stocktwits_data.keys())
        insider_tickers = set(insider_data.keys())
        earnings_tickers = set(earnings_data.keys())
        alpaca_news_tickers = set(alpaca_news_data.keys())
        hackernews_tickers = set(hackernews_data.keys())
        telegram_tickers = set(telegram_data.keys())
        bluesky_tickers = set(bluesky_data.keys())
        youtube_tickers = set(youtube_data.keys())
        news_tickers = await self._discover_from_news()
        sec_tickers = await self._discover_from_sec() if deep_mode else set()

        all_candidates = (
            set(base_tickers)
            | reddit_tickers
            | discord_tickers
            | stocktwits_tickers
            | insider_tickers
            | earnings_tickers
            | alpaca_news_tickers
            | hackernews_tickers
            | telegram_tickers
            | bluesky_tickers
            | youtube_tickers
            | news_tickers
            | sec_tickers
        )

        new_tickers = all_candidates - set(base_tickers)
        if new_tickers:
            await self._persist_discovered_tickers(sorted(new_tickers))

        logger.info(
            f"Discovery: {len(base_tickers)} base + {len(reddit_tickers)} Reddit + "
            f"{len(discord_tickers)} Discord + {len(stocktwits_tickers)} StockTwits + "
            f"{len(insider_tickers)} Insider + {len(earnings_tickers)} Earnings + "
            f"{len(alpaca_news_tickers)} AlpacaNews + {len(hackernews_tickers)} HN + "
            f"{len(telegram_tickers)} Telegram + {len(bluesky_tickers)} Bluesky + "
            f"{len(youtube_tickers)} YouTube + "
            f"{len(news_tickers)} News + {len(sec_tickers)} SEC = "
            f"{len(all_candidates)} candidates ({len(new_tickers)} new)"
        )

        return sorted(all_candidates), reddit_data, discord_data, stocktwits_data, insider_data, earnings_data, alpaca_news_data, hackernews_data, telegram_data, bluesky_data, youtube_data

    async def _persist_discovered_tickers(self, new_tickers: list[str]):
        from stradegy.db import Ticker
        from stradegy.engine.data.store import DataStore

        if not new_tickers:
            return

        try:
            async with async_session() as session:
                store = DataStore(session)
                existing = set()
                result = await session.execute(
                    select(Ticker.symbol).where(Ticker.symbol.in_(new_tickers))
                )
                existing = {row[0] for row in result.all()}

                to_add = [t for t in new_tickers if t not in existing]
                for symbol in to_add:
                    try:
                        await store.save_ticker(
                            symbol=symbol,
                            source="discovery",
                            is_active=True,
                            is_watched=False,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save discovered ticker {symbol}: {e}")

                logger.info(f"Persisted {len(to_add)} discovered tickers to database")
        except Exception as e:
            logger.error(f"Failed to persist discovered tickers: {e}")

    def _extract_tickers_from_mentions(self, mentions: list) -> set[str]:
        tickers = set()
        for m in mentions:
            try:
                tickers.add(m.ticker_symbol.upper())
            except Exception:
                pass
        return tickers

    def _group_insider_by_ticker(self, signals: list) -> dict[str, list]:
        grouped = {}
        for s in signals:
            try:
                ts = s.ticker_symbol.upper()
                if ts not in grouped:
                    grouped[ts] = []
                grouped[ts].append(s)
            except Exception:
                pass
        return grouped

    def _group_earnings_by_ticker(self, signals: list) -> dict[str, list]:
        grouped = {}
        for s in signals:
            try:
                ts = s.ticker_symbol.upper()
                if ts not in grouped:
                    grouped[ts] = []
                grouped[ts].append(s)
            except Exception:
                pass
        return grouped

    async def _discover_from_news(self) -> set[str]:
        try:
            if not self.news.client:
                return set()
            import finnhub
            news = self.news.client.general_news("general", min_id=0)
            if not news:
                return set()
            tickers = set()
            for article in news[:50]:  # Limit to recent 50 articles
                headline = article.get("headline", "")
                summary = article.get("summary", "")
                text = f"{headline} {summary}"
                matches = TICKER_PATTERN.findall(text)
                for m in matches:
                    if len(m) >= 2 and len(m) <= 5:
                        tickers.add(m.upper())
            logger.info(f"News discovery: {len(tickers)} tickers found from {len(news)} articles")
            return tickers
        except Exception as e:
            logger.warning(f"News discovery failed: {e}")
            return set()

    async def _discover_from_sec(self) -> set[str]:
        try:
            from edgar import set_identity, Company
            set_identity("Stradegy contact@stradegy.dev")
            return set()
        except Exception as e:
            logger.warning(f"SEC discovery failed: {e}")
            return set()

    async def _safe_scan(self, scan_fn, **kwargs):
        try:
            return await scan_fn(**kwargs)
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return []

    async def _get_active_tickers(self) -> list[str]:
        from stradegy.engine.data.store import DataStore
        async with async_session() as session:
            store = DataStore(session)
            tickers = await store.get_active_tickers()
            return [t.symbol for t in tickers]

    async def _run_full_pipeline(
        self,
        candidate_tickers: list[str],
        reddit_data: dict[str, list] = None,
        discord_data: dict[str, list] = None,
        stocktwits_data: dict[str, list] = None,
        insider_data: dict[str, list] = None,
        earnings_data: dict[str, list] = None,
        alpaca_news_data: dict[str, list] = None,
        hackernews_data: dict[str, list] = None,
        telegram_data: dict[str, list] = None,
        bluesky_data: dict[str, list] = None,
        youtube_data: dict[str, list] = None,
        deep_mode: bool = False,
    ):
        from stradegy.engine.data.store import DataStore
        from stradegy.engine.research.technical_filter import TechnicalFilter

        logger.info(f"Running full pipeline on {len(candidate_tickers)} candidates")
        reddit_data = reddit_data or {}
        discord_data = discord_data or {}
        stocktwits_data = stocktwits_data or {}
        insider_data = insider_data or {}
        earnings_data = earnings_data or {}
        alpaca_news_data = alpaca_news_data or {}
        hackernews_data = hackernews_data or {}
        telegram_data = telegram_data or {}
        bluesky_data = bluesky_data or {}
        youtube_data = youtube_data or {}

        async with async_session() as session:
            store = DataStore(session)
            gems_found = []

            for ticker in candidate_tickers:
                try:
                    ticker_reddit = reddit_data.get(ticker, [])
                    ticker_discord = discord_data.get(ticker, [])
                    ticker_stocktwits = stocktwits_data.get(ticker, [])
                    ticker_insider = insider_data.get(ticker, [])
                    ticker_earnings = earnings_data.get(ticker, [])
                    ticker_alpaca_news = alpaca_news_data.get(ticker, [])
                    ticker_hackernews = hackernews_data.get(ticker, [])
                    ticker_telegram = telegram_data.get(ticker, [])
                    ticker_bluesky = bluesky_data.get(ticker, [])
                    ticker_youtube = youtube_data.get(ticker, [])

                    technical = None
                    try:
                        tech_filter = TechnicalFilter(store)
                        technical = await tech_filter.analyze(ticker)
                    except Exception as e:
                        logger.warning(f"Technical filter failed for {ticker}: {e}")

                    trends = None
                    try:
                        trends = await self.trends.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"Trends scan failed for {ticker}: {e}")

                    sec_filing = None
                    news_sentiment = {}

                    has_social = ticker_reddit or ticker_discord or ticker_stocktwits or ticker_insider or ticker_earnings
                    if has_social or deep_mode or (technical and technical.overall_pass):
                        try:
                            sec_filing = self.sec.analyze_10k(ticker)
                        except Exception as e:
                            logger.warning(f"SEC scan failed for {ticker}: {e}")

                        try:
                            news_sentiment = await self.news.aggregate_sentiment(ticker, limit=10)
                        except Exception as e:
                            logger.warning(f"News scan failed for {ticker}: {e}")

                    fred_indicators = None
                    try:
                        fred_indicators = await self.fred.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"FRED scan failed for {ticker}: {e}")

                    fear_greed_signals = None
                    try:
                        fear_greed_signals = await self.fear_greed.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"FearGreed scan failed for {ticker}: {e}")

                    options_signals = None
                    try:
                        options_signals = await self.options.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"Options scan failed for {ticker}: {e}")

                    twelve_data_quotes = None
                    try:
                        twelve_data_quotes = await self.twelve_data.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"TwelveData scan failed for {ticker}: {e}")

                    fmp_grades = None
                    try:
                        fmp_grades = await self.fmp.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"FMP scan failed for {ticker}: {e}")

                    finra_si = None
                    try:
                        finra_si = await self.finra.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"FINRA scan failed for {ticker}: {e}")

                    keyvex_signals = None
                    try:
                        keyvex_signals = await self.keyvex.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"KeyVex scan failed for {ticker}: {e}")

                    adanos_sentiments = None
                    try:
                        adanos_sentiments = await self.adanos.scan_ticker(ticker)
                    except Exception as e:
                        logger.warning(f"Adanos scan failed for {ticker}: {e}")

                    gem = self.gem_detector.detect(
                        ticker=ticker,
                        reddit_mentions=ticker_reddit,
                        discord_mentions=ticker_discord,
                        stocktwits_mentions=ticker_stocktwits,
                        insider_signals=ticker_insider,
                        trends=trends,
                        earnings=ticker_earnings,
                        sec_filing=sec_filing,
                        news_sentiment=news_sentiment,
                        technical=technical,
                        alpaca_news_mentions=ticker_alpaca_news,
                        hackernews_mentions=ticker_hackernews,
                        telegram_mentions=ticker_telegram,
                        bluesky_mentions=ticker_bluesky,
                        youtube_mentions=ticker_youtube,
                        fred_indicators=fred_indicators,
                        fear_greed_signals=fear_greed_signals,
                        options_signals=options_signals,
                        twelve_data_quotes=twelve_data_quotes,
                        fmp_grades=fmp_grades,
                        finra_si=finra_si,
                        keyvex_signals=keyvex_signals,
                        adanos_sentiments=adanos_sentiments,
                    )

                    from stradegy.engine.research.db import GemSignalRecord, ResearchStore
                    research_store = ResearchStore(session)
                    record = GemSignalRecord(
                        ticker_symbol=gem.ticker_symbol,
                        reddit_score=gem.reddit_score,
                        discord_score=gem.discord_score,
                        stocktwits_score=gem.stocktwits_score,
                        insider_score=gem.insider_score,
                        trends_score=gem.trends_score,
                        earnings_score=gem.earnings_score,
                        sec_score=gem.sec_score,
                        news_score=gem.news_score,
                        technical_score=gem.technical_score,
                        alpaca_news_score=gem.alpaca_news_score,
                        hackernews_score=gem.hackernews_score,
                        telegram_score=gem.telegram_score,
                        bluesky_score=gem.bluesky_score,
                        youtube_score=gem.youtube_score,
                        fred_score=gem.fred_score,
                        fear_greed_score=gem.fear_greed_score,
                        options_score=gem.options_score,
                        twelve_data_score=gem.twelve_data_score,
                        fmp_score=gem.fmp_score,
                        finra_score=gem.finra_score,
                        keyvex_score=gem.keyvex_score,
                        adanos_score=gem.adanos_score,
                        total_score=gem.total_score,
                        classification=gem.classification.value,
                        source_count=gem.source_count,
                        evidence_urls=gem.evidence_urls,
                        alerted=False,
                        status="pending",
                    )
                    await research_store.save_gem_signal(record)

                    if gem.classification in (GemClassification.STRONG, GemClassification.POTENTIAL):
                        self.validator.store = store
                        validation = await self.validator.validate(gem)
                        if validation.is_valid:
                            gems_found.append(gem)
                            await research_store.mark_gem_alerted(record.id)
                            await asyncio.gather(
                                self.telegram.send_gem_alert(gem),
                                self.discord_alerts.send_gem_alert(gem),
                                self.whatsapp.send_gem_alert(gem),
                                return_exceptions=True,
                            )
                            logger.info(f"Valid gem alert sent for {ticker}: {gem.total_score}")

                            if settings.autonomy_mode == "full":
                                await self._auto_execute_gem(gem, store, session)
                        else:
                            logger.info(f"Gem rejected for {ticker}: {validation.failures}")
                    else:
                        logger.info(f"Low-confidence gem stored for {ticker}: score={gem.total_score}, class={gem.classification.value}, sources={gem.source_count}")

                except Exception as e:
                    logger.error(f"Pipeline error for {ticker}: {e}")

            logger.info(
                f"Pipeline complete: {len(candidate_tickers)} candidates scanned, "
                f"{len(gems_found)} gems found"
            )

    def _mentions_to_dict(self, mentions: list) -> dict[str, list]:
        grouped = {}
        for m in mentions:
            try:
                ts = m.ticker_symbol.upper()
                if ts not in grouped:
                    grouped[ts] = []
                entry = {}
                if hasattr(m, "sentiment_compound"):
                    entry["sentiment_compound"] = m.sentiment_compound
                else:
                    entry["sentiment_compound"] = 0.0
                if hasattr(m, "upvote_ratio"):
                    entry["upvote_ratio"] = m.upvote_ratio
                if hasattr(m, "velocity_vs_avg"):
                    entry["velocity_vs_avg"] = m.velocity_vs_avg
                if hasattr(m, "post_url"):
                    entry["post_url"] = m.post_url
                if hasattr(m, "article_url"):
                    entry["article_url"] = m.article_url
                if hasattr(m, "story_url"):
                    entry["story_url"] = m.story_url
                if hasattr(m, "video_url"):
                    entry["video_url"] = m.video_url
                if hasattr(m, "message_url"):
                    entry["message_url"] = m.message_url
                if hasattr(m, "num_reactions"):
                    entry["num_reactions"] = m.num_reactions
                if hasattr(m, "reactions"):
                    entry["reactions"] = m.reactions
                if hasattr(m, "reply_count"):
                    entry["reply_count"] = m.reply_count
                if hasattr(m, "replies"):
                    entry["replies"] = m.replies
                if hasattr(m, "likes"):
                    entry["likes"] = m.likes
                if hasattr(m, "reshares"):
                    entry["reshares"] = m.reshares
                if hasattr(m, "reposts"):
                    entry["reposts"] = m.reposts
                if hasattr(m, "watchlist_count"):
                    entry["watchlist_count"] = m.watchlist_count
                if hasattr(m, "points"):
                    entry["points"] = m.points
                if hasattr(m, "num_comments"):
                    entry["num_comments"] = m.num_comments
                if hasattr(m, "views"):
                    entry["views"] = m.views
                if hasattr(m, "channel_name"):
                    entry["channel_name"] = m.channel_name
                if hasattr(m, "message_id"):
                    entry["message_id"] = m.message_id
                if hasattr(m, "sentiment_label"):
                    entry["sentiment_label"] = m.sentiment_label
                if hasattr(m, "comment_text"):
                    entry["comment_text"] = m.comment_text
                grouped[ts].append(entry)
            except Exception:
                pass
        return grouped

    async def _auto_execute_gem(self, gem: GemSignal, store, session):
        logger.info(f"Auto-executing gem for {gem.ticker_symbol} (full autonomy)")
        try:
            from stradegy.engine.execution.alpaca_client import AlpacaClient
            from stradegy.engine.risk.manager import RiskManager
            from stradegy.db import Trade as TradeModel

            try:
                import pytz
                et = pytz.timezone("US/Eastern")
            except ImportError:
                et = timezone(timedelta(hours=-5))
            now = datetime.now(et)
            market_closed = (
                now.weekday() >= 5
                or now.hour < 9
                or (now.hour == 9 and now.minute < 30)
                or now.hour >= 16
            )
            if market_closed:
                logger.warning(f"Market closed — skipping auto-execution for {gem.ticker_symbol}")
                return

            client = AlpacaClient()
            account = await client.get_account()
            if not account:
                logger.error("Could not fetch Alpaca account for auto-execution")
                return

            equity = account.get("equity", 0.0)
            rm = RiskManager()

            history = await store.get_portfolio_history(days=90)
            peak_equity = equity
            for h in history:
                if h.get("peak_equity") and h["peak_equity"] > peak_equity:
                    peak_equity = h["peak_equity"]
                elif h.get("equity") and h["equity"] > peak_equity:
                    peak_equity = h["equity"]

            pdt_data = rm.check_pdt([])
            emergency = rm.emergency_check(equity, peak_equity, pdt_data, [])
            if emergency["should_halt_trading"]:
                logger.warning(f"TRADING HALTED: {emergency['emergencies']}")
                return

            positions = await client.get_positions()
            tier = rm._tier_config(equity)
            if len(positions) >= tier["max_positions"]:
                logger.warning(f"Max positions reached ({len(positions)}/{tier['max_positions']})")
                return

            df = await store.get_ohlcv_dataframe(gem.ticker_symbol, limit=30)
            atr = 0.0
            if df is not None and len(df) >= 14:
                import pandas as pd
                hl = df["high"] - df["low"]
                hc = abs(df["high"] - df["close"].shift())
                lc = abs(df["low"] - df["close"].shift())
                tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean().iloc[-1]

            latest_price = await store.get_latest_price(gem.ticker_symbol)
            price = float(latest_price) if latest_price else 0.0
            if price <= 0:
                logger.warning(f"Invalid price for {gem.ticker_symbol}: {price}")
                return

            sizing = rm.calculate_position_size(equity, atr, price)
            if sizing["shares"] <= 0:
                logger.warning(f"Position sizing returned 0 shares for {gem.ticker_symbol}")
                return

            order_result = await client.submit_order(
                symbol=gem.ticker_symbol,
                qty=sizing["shares"],
                side="buy",
                order_type="market",
            )
            if order_result and not order_result.get("error"):
                order_id = order_result.get("id")
                fill_status = "submitted"
                filled_qty = sizing["shares"]
                if order_id:
                    fill_result = await client.poll_order_fill(order_id, timeout=30, interval=2)
                    fill_status = fill_result.get("status", "unknown")
                    filled_qty = float(fill_result.get("filled_qty", sizing["shares"]))
                    logger.info(
                        f"Auto-order {order_id} for {gem.ticker_symbol}: {fill_status} ({filled_qty}/{sizing['shares']} shares)"
                    )
                else:
                    logger.info(f"Auto-order submitted for {gem.ticker_symbol} (no order ID)")

                gem_record = GemSignalRecord(
                    ticker_symbol=gem.ticker_symbol,
                    reddit_score=gem.reddit_score,
                    discord_score=gem.discord_score,
                    stocktwits_score=gem.stocktwits_score,
                    insider_score=gem.insider_score,
                    trends_score=gem.trends_score,
                    earnings_score=gem.earnings_score,
                    sec_score=gem.sec_score,
                    news_score=gem.news_score,
                    technical_score=gem.technical_score,
                    alpaca_news_score=gem.alpaca_news_score,
                    hackernews_score=gem.hackernews_score,
                    telegram_score=gem.telegram_score,
                    bluesky_score=gem.bluesky_score,
                    youtube_score=gem.youtube_score,
                    fred_score=gem.fred_score,
                    fear_greed_score=gem.fear_greed_score,
                    options_score=gem.options_score,
                    twelve_data_score=gem.twelve_data_score,
                    fmp_score=gem.fmp_score,
                    finra_score=gem.finra_score,
                    keyvex_score=gem.keyvex_score,
                    adanos_score=gem.adanos_score,
                    total_score=gem.total_score,
                    classification=gem.classification.value,
                    source_count=gem.source_count,
                    evidence_urls=gem.evidence_urls,
                    status="executed",
                )
                session.add(gem_record)
                await session.commit()
                await session.refresh(gem_record)

                trade = TradeModel(
                    ticker_symbol=gem.ticker_symbol,
                    action="buy",
                    price=Decimal(str(price)),
                    shares=int(filled_qty),
                    strategy="ensemble",
                    signal_confidence=gem.total_score / 100.0,
                    order_id=str(order_id) if order_id else None,
                    status="filled" if fill_status.lower() == "filled" else "submitted",
                    mode="paper" if settings.paper_trading else "live",
                    gem_id=gem_record.id if gem_record else None,
                    notes=f"Auto-executed via research pipeline. ATR={atr:.2f}, score={gem.total_score}",
                )
                session.add(trade)
                await session.commit()
                logger.info(f"Auto-execution complete for {gem.ticker_symbol}: trade_id={trade.id}")
            else:
                logger.error(f"Auto-order submission failed for {gem.ticker_symbol}: {order_result}")
        except Exception as e:
            logger.error(f"Auto-execution failed for {gem.ticker_symbol}: {e}")
