from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class SignalSource(str, Enum):
    REDDIT = "reddit"
    DISCORD = "discord"
    SEC = "sec"
    NEWS = "news"
    TECHNICAL = "technical"


class GemClassification(str, Enum):
    STRONG = "strong_gem"
    POTENTIAL = "potential_gem"
    WATCHLIST = "watchlist"
    DISCARD = "discard"


class RedditMention(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    subreddit: str
    post_id: str
    post_url: str
    title: str
    created_utc: datetime
    score: int = Field(..., ge=0)
    num_comments: int = Field(..., ge=0)
    upvote_ratio: float = Field(..., ge=0.0, le=1.0)
    sentiment_compound: float = Field(..., ge=-1.0, le=1.0)
    mention_count_1h: int = Field(..., ge=0)
    mention_count_6h: int = Field(..., ge=0)
    mention_count_24h: int = Field(..., ge=0)
    velocity_vs_avg: float
    author: str | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class DiscordMention(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    guild_id: str
    channel_id: str
    channel_name: str
    message_id: str
    message_url: str
    content: str
    created_utc: datetime
    score: int = Field(..., ge=0)
    num_reactions: int = Field(..., ge=0)
    reply_count: int = Field(..., ge=0)
    sentiment_compound: float = Field(..., ge=-1.0, le=1.0)
    mention_count_1h: int = Field(..., ge=0)
    mention_count_6h: int = Field(..., ge=0)
    mention_count_24h: int = Field(..., ge=0)
    velocity_vs_avg: float
    author: str | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class SECFiling(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    filing_type: str
    filing_date: datetime
    filing_url: str
    revenue_growth_yoy: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    insider_net_buys: int = 0
    cash_to_debt_ratio: float | None = None
    risk_factors_changed: bool = False

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class NewsArticle(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    headline: str
    article_url: str
    source: str
    published_at: datetime
    finbert_sentiment: float = Field(..., ge=-1.0, le=1.0)
    finbert_confidence: float = Field(..., ge=0.0, le=1.0)
    finbert_label: str

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class TechnicalScore(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    price: float = Field(..., gt=0)
    price_vs_sma15: float
    price_vs_20day_high: float
    volume_vs_50day_avg: float
    market_cap_millions: float | None = None
    rsi_14: float | None = Field(None, ge=0, le=100)
    passes_price_filter: bool
    passes_volume_filter: bool
    passes_market_cap_filter: bool
    passes_rsi_filter: bool
    overall_pass: bool

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class SourceScore(BaseModel):
    source: SignalSource
    raw_score: float = Field(..., ge=0.0, le=100.0)
    weight: float = Field(..., gt=0)
    weighted_score: float = Field(..., ge=0.0, le=100.0)
    evidence: list[str] = Field(default_factory=list)


class GemSignal(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    reddit_score: float = Field(0.0, ge=0.0, le=25.0)
    discord_score: float = Field(0.0, ge=0.0, le=25.0)
    sec_score: float = Field(0.0, ge=0.0, le=30.0)
    news_score: float = Field(0.0, ge=0.0, le=20.0)
    technical_score: float = Field(0.0, ge=0.0, le=25.0)
    total_score: float = Field(0.0, ge=0.0, le=100.0)
    classification: GemClassification = GemClassification.DISCARD
    source_count: int = Field(0, ge=0, le=5)
    sources: list[SourceScore] = Field(default_factory=list)
    evidence_urls: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def compute_scores(self) -> "GemSignal":
        self.total_score = round(
            self.reddit_score + self.discord_score + self.sec_score + self.news_score + self.technical_score,
            2,
        )
        if self.total_score >= 80:
            self.classification = GemClassification.STRONG
        elif self.total_score >= 65:
            self.classification = GemClassification.POTENTIAL
        elif self.total_score >= 50:
            self.classification = GemClassification.WATCHLIST
        else:
            self.classification = GemClassification.DISCARD
        return self


class ValidationResult(BaseModel):
    ticker_symbol: str
    is_valid: bool
    checks: dict[str, bool] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
    source_count: int = 0

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()
