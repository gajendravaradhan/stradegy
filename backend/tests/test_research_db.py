from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from stradegy.db import async_session
from stradegy.engine.research.db import (
    GemSignalRecord,
    NewsSentimentRecord,
    RedditMentionRecord,
    ResearchStore,
    SECFilingRecord,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def store():
    from stradegy.db import Base, engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        store = ResearchStore(session)
        yield store
        await session.rollback()


class TestRedditMentionRecord:
    @pytest.mark.anyio
    async def test_save_and_retrieve(self, store):
        record = RedditMentionRecord(
            ticker_symbol="AAPL",
            subreddit="wallstreetbets",
            post_id="test123",
            post_url="https://reddit.com/r/wsb/test123",
            title="AAPL to the moon",
            created_utc=datetime.now(timezone.utc),
            score=100,
            num_comments=25,
            upvote_ratio=0.9,
            sentiment_compound=0.8,
            mention_count_1h=3,
            mention_count_6h=10,
            mention_count_24h=30,
            velocity_vs_avg=2.5,
        )
        saved = await store.save_reddit_mention(record)
        assert saved.id is not None

        mentions = await store.get_reddit_mentions("AAPL")
        assert len(mentions) == 1
        assert mentions[0].ticker_symbol == "AAPL"
        assert mentions[0].score == 100

    @pytest.mark.anyio
    async def test_multiple_mentions(self, store):
        for i in range(3):
            record = RedditMentionRecord(
                ticker_symbol="MSFT",
                subreddit="stocks",
                post_id=f"post{i}",
                post_url=f"https://reddit.com/r/stocks/post{i}",
                title=f"MSFT post {i}",
                created_utc=datetime.now(timezone.utc),
                score=50 + i,
                num_comments=10,
                upvote_ratio=0.8,
                sentiment_compound=0.5,
                mention_count_1h=1,
                mention_count_6h=5,
                mention_count_24h=15,
                velocity_vs_avg=1.5,
            )
            await store.save_reddit_mention(record)

        mentions = await store.get_reddit_mentions("MSFT", limit=2)
        assert len(mentions) == 2


class TestSECFilingRecord:
    @pytest.mark.anyio
    async def test_save_and_retrieve(self, store):
        record = SECFilingRecord(
            ticker_symbol="TSLA",
            filing_type="10-K",
            filing_date=datetime.now(timezone.utc),
            filing_url="https://sec.gov/...",
            revenue_growth_yoy=0.32,
            gross_margin=0.19,
            operating_margin=0.12,
            insider_net_buys=5,
            cash_to_debt_ratio=2.5,
        )
        saved = await store.save_sec_filing(record)
        assert saved.id is not None

        filings = await store.get_sec_filings("TSLA")
        assert len(filings) == 1
        assert filings[0].filing_type == "10-K"
        assert filings[0].revenue_growth_yoy == 0.32


class TestNewsSentimentRecord:
    @pytest.mark.anyio
    async def test_save_and_retrieve(self, store):
        record = NewsSentimentRecord(
            ticker_symbol="NVDA",
            headline="NVDA beats earnings",
            article_url="https://example.com/news",
            source="Bloomberg",
            published_at=datetime.now(timezone.utc),
            finbert_sentiment=0.85,
            finbert_confidence=0.92,
            finbert_label="positive",
        )
        saved = await store.save_news_sentiment(record)
        assert saved.id is not None

        sentiments = await store.get_news_sentiments("NVDA")
        assert len(sentiments) == 1
        assert sentiments[0].finbert_label == "positive"


class TestGemSignalRecord:
    @pytest.mark.anyio
    async def test_save_and_query_by_score(self, store):
        record = GemSignalRecord(
            ticker_symbol="PLUG",
            reddit_score=20.0,
            sec_score=25.0,
            news_score=15.0,
            technical_score=20.0,
            total_score=80.0,
            classification="strong_gem",
            source_count=4,
            evidence_urls=["https://reddit.com/...", "https://sec.gov/..."],
        )
        saved = await store.save_gem_signal(record)
        assert saved.id is not None
        assert saved.alerted is False

        gems = await store.get_gem_signals(min_score=70.0)
        assert len(gems) == 1
        assert gems[0].ticker_symbol == "PLUG"

    @pytest.mark.anyio
    async def test_query_by_ticker(self, store):
        record = GemSignalRecord(
            ticker_symbol="AMD",
            total_score=45.0,
            classification="discard",
            source_count=1,
        )
        await store.save_gem_signal(record)

        gems = await store.get_gem_signals(ticker_symbol="AMD")
        assert len(gems) == 1
        assert gems[0].total_score == 45.0

    @pytest.mark.anyio
    async def test_mark_alerted(self, store):
        record = GemSignalRecord(
            ticker_symbol="INTC",
            total_score=70.0,
            classification="potential_gem",
            source_count=3,
        )
        saved = await store.save_gem_signal(record)
        await store.mark_gem_alerted(saved.id)

        result = await store.get_latest_gem_signal("INTC")
        assert result is not None
        assert result.alerted is True

    @pytest.mark.anyio
    async def test_no_results_for_missing_ticker(self, store):
        gems = await store.get_gem_signals(ticker_symbol="FAKE123")
        assert len(gems) == 0
