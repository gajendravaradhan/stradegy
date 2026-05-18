from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from stradegy.db import Base


class RedditMentionRecord(Base):
    __tablename__ = "reddit_mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    subreddit: Mapped[str] = mapped_column(String(64), nullable=False)
    post_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    post_url: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    created_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    num_comments: Mapped[int] = mapped_column(Integer, default=0)
    upvote_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_compound: Mapped[float] = mapped_column(Float, default=0.0)
    mention_count_1h: Mapped[int] = mapped_column(Integer, default=0)
    mention_count_6h: Mapped[int] = mapped_column(Integer, default=0)
    mention_count_24h: Mapped[int] = mapped_column(Integer, default=0)
    velocity_vs_avg: Mapped[float] = mapped_column(Float, default=0.0)
    author: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class SECFilingRecord(Base):
    __tablename__ = "sec_filing_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    filing_type: Mapped[str] = mapped_column(String(16), nullable=False)
    filing_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    filing_url: Mapped[str] = mapped_column(String(512), nullable=False)
    revenue_growth_yoy: Mapped[float] = mapped_column(Float, nullable=True)
    gross_margin: Mapped[float] = mapped_column(Float, nullable=True)
    operating_margin: Mapped[float] = mapped_column(Float, nullable=True)
    insider_net_buys: Mapped[int] = mapped_column(Integer, default=0)
    cash_to_debt_ratio: Mapped[float] = mapped_column(Float, nullable=True)
    risk_factors_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class NewsSentimentRecord(Base):
    __tablename__ = "news_sentiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    article_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finbert_sentiment: Mapped[float] = mapped_column(Float, default=0.0)
    finbert_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    finbert_label: Mapped[str] = mapped_column(String(16), default="neutral")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class DiscordMentionRecord(Base):
    __tablename__ = "discord_mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    guild_id: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_name: Mapped[str] = mapped_column(String(128), nullable=False)
    message_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    message_url: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(String(2000), nullable=False)
    created_utc: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0)
    num_reactions: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_compound: Mapped[float] = mapped_column(Float, default=0.0)
    mention_count_1h: Mapped[int] = mapped_column(Integer, default=0)
    mention_count_6h: Mapped[int] = mapped_column(Integer, default=0)
    mention_count_24h: Mapped[int] = mapped_column(Integer, default=0)
    velocity_vs_avg: Mapped[float] = mapped_column(Float, default=0.0)
    author: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class GemSignalRecord(Base):
    __tablename__ = "gem_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker_symbol: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    reddit_score: Mapped[float] = mapped_column(Float, default=0.0)
    discord_score: Mapped[float] = mapped_column(Float, default=0.0)
    sec_score: Mapped[float] = mapped_column(Float, default=0.0)
    news_score: Mapped[float] = mapped_column(Float, default=0.0)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    classification: Mapped[str] = mapped_column(String(32), default="discard")
    source_count: Mapped[int] = mapped_column(Integer, default=0)
    evidence_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    alerted: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    actioned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class ResearchStore:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_discord_mention(self, record: DiscordMentionRecord) -> DiscordMentionRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_discord_mentions(
        self, ticker_symbol: str, limit: int = 100
    ) -> list[DiscordMentionRecord]:
        result = await self.session.execute(
            select(DiscordMentionRecord)
            .where(DiscordMentionRecord.ticker_symbol == ticker_symbol.upper())
            .order_by(DiscordMentionRecord.created_utc.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def save_reddit_mention(self, record: RedditMentionRecord) -> RedditMentionRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_reddit_mentions(
        self, ticker_symbol: str, limit: int = 100
    ) -> list[RedditMentionRecord]:
        result = await self.session.execute(
            select(RedditMentionRecord)
            .where(RedditMentionRecord.ticker_symbol == ticker_symbol.upper())
            .order_by(RedditMentionRecord.created_utc.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def save_sec_filing(self, record: SECFilingRecord) -> SECFilingRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_sec_filings(
        self, ticker_symbol: str, limit: int = 50
    ) -> list[SECFilingRecord]:
        result = await self.session.execute(
            select(SECFilingRecord)
            .where(SECFilingRecord.ticker_symbol == ticker_symbol.upper())
            .order_by(SECFilingRecord.filing_date.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def save_news_sentiment(self, record: NewsSentimentRecord) -> NewsSentimentRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_news_sentiments(
        self, ticker_symbol: str, limit: int = 100
    ) -> list[NewsSentimentRecord]:
        result = await self.session.execute(
            select(NewsSentimentRecord)
            .where(NewsSentimentRecord.ticker_symbol == ticker_symbol.upper())
            .order_by(NewsSentimentRecord.published_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def save_gem_signal(self, record: GemSignalRecord) -> GemSignalRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_gem_signals(
        self,
        ticker_symbol: str | None = None,
        min_score: float = 0.0,
        limit: int = 100,
    ) -> list[GemSignalRecord]:
        stmt = select(GemSignalRecord).where(GemSignalRecord.total_score >= min_score)
        if ticker_symbol:
            stmt = stmt.where(GemSignalRecord.ticker_symbol == ticker_symbol.upper())
        stmt = stmt.order_by(GemSignalRecord.total_score.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_latest_gem_signal(self, ticker_symbol: str) -> GemSignalRecord | None:
        result = await self.session.execute(
            select(GemSignalRecord)
            .where(GemSignalRecord.ticker_symbol == ticker_symbol.upper())
            .order_by(GemSignalRecord.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_gem_alerted(self, gem_id: int):
        result = await self.session.execute(
            select(GemSignalRecord).where(GemSignalRecord.id == gem_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.alerted = True
            await self.session.commit()

    async def approve_gem(self, gem_id: int) -> GemSignalRecord | None:
        result = await self.session.execute(
            select(GemSignalRecord).where(GemSignalRecord.id == gem_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = "approved"
            record.actioned_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def reject_gem(self, gem_id: int) -> GemSignalRecord | None:
        result = await self.session.execute(
            select(GemSignalRecord).where(GemSignalRecord.id == gem_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = "rejected"
            record.actioned_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(record)
        return record

    async def execute_gem(self, gem_id: int) -> GemSignalRecord | None:
        result = await self.session.execute(
            select(GemSignalRecord).where(GemSignalRecord.id == gem_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = "executed"
            record.actioned_at = datetime.now(timezone.utc)
            await self.session.commit()
            await self.session.refresh(record)
        return record
