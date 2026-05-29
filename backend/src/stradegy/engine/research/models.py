from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class SignalSource(str, Enum):
    REDDIT = "reddit"
    DISCORD = "discord"
    STOCKTWITS = "stocktwits"
    INSIDER = "insider"
    TRENDS = "trends"
    EARNINGS = "earnings"
    SEC = "sec"
    NEWS = "news"
    TECHNICAL = "technical"
    FMP = "fmp"
    FINRA = "finra"
    KEYVEX = "keyvex"
    ADANOS = "adanos"
    ALPACA_NEWS = "alpaca_news"
    HACKERNEWS = "hackernews"
    TELEGRAM = "telegram"
    BLUESKY = "bluesky"
    YOUTUBE = "youtube"
    FRED = "fred"
    FEAR_GREED = "fear_greed"
    OPTIONS = "options"
    TWELVE_DATA = "twelve_data"


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


class StockTwitsMention(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    message_id: str
    message_url: str
    content: str
    created_utc: datetime
    sentiment_compound: float = Field(..., ge=-1.0, le=1.0)
    likes: int = Field(..., ge=0)
    reshares: int = Field(..., ge=0)
    watchlist_count: int = Field(..., ge=0)
    author: str | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class InsiderSignal(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    insider_name: str
    insider_title: str
    transaction_date: datetime
    transaction_type: str
    shares: int
    price: float
    total_value: float
    filing_url: str
    is_cluster: bool = False

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class TrendsSignal(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    interest_score: float = Field(..., ge=0.0, le=100.0)
    interest_vs_90d_avg: float
    direction: str
    region_breakdown: dict[str, float] | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class EarningsSignal(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    report_date: datetime
    eps_estimate: float | None = None
    eps_actual: float | None = None
    revenue_estimate: float | None = None
    revenue_actual: float | None = None
    surprise_pct: float | None = None
    is_upcoming: bool = False
    days_until: int = 0

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


class AlpacaNewsArticle(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    headline: str
    article_url: str
    source: str
    published_at: datetime
    sentiment_compound: float = Field(..., ge=-1.0, le=1.0)
    sentiment_label: str
    tickers_tags: list[str] = Field(default_factory=list)
    author: str | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class HackerNewsMention(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    story_id: str
    story_url: str
    title: str
    created_utc: datetime
    points: int = Field(..., ge=0)
    num_comments: int = Field(..., ge=0)
    sentiment_compound: float = Field(..., ge=-1.0, le=1.0)
    author: str | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class TelegramMention(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    channel_name: str
    message_id: str
    content: str
    created_utc: datetime
    views: int = Field(..., ge=0)
    reactions: int = Field(..., ge=0)
    sentiment_compound: float = Field(..., ge=-1.0, le=1.0)
    author: str | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class BlueskyMention(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    post_id: str
    post_url: str
    content: str
    created_utc: datetime
    likes: int = Field(..., ge=0)
    reposts: int = Field(..., ge=0)
    replies: int = Field(..., ge=0)
    sentiment_compound: float = Field(..., ge=-1.0, le=1.0)
    author: str | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class YouTubeMention(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    video_id: str
    video_url: str
    comment_id: str
    comment_text: str
    created_utc: datetime
    likes: int = Field(..., ge=0)
    sentiment_compound: float = Field(..., ge=-1.0, le=1.0)
    author: str | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class FMPGradeChange(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    new_grade: str
    previous_grade: str
    action: str
    grading_company: str
    price_target: float | None = None
    previous_price_target: float | None = None
    change_date: datetime

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class FINRAShortInterest(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    settlement_date: datetime
    short_interest: int = Field(..., ge=0)
    average_daily_volume: int = Field(..., ge=0)
    days_to_cover: float | None = None
    short_interest_ratio: float | None = None

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class KeyVexSignal(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    dark_pool_volume: int = Field(0, ge=0)
    dark_pool_trade_count: int = Field(0, ge=0)
    congressional_trade_amount: float | None = None
    congressional_trade_type: str | None = None
    congressional_rep_name: str | None = None
    insider_shares: int = Field(0, ge=0)
    insider_transaction_type: str | None = None
    institution_holdings_change_pct: float | None = None
    sec_fails_to_deliver: int = Field(0, ge=0)
    signal_score: float = Field(0.0, ge=0.0, le=100.0)
    report_date: datetime

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class AdanosSentimentScore(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    reddit_sentiment: float = Field(0.0, ge=-1.0, le=1.0)
    reddit_mentions: int = Field(0, ge=0)
    x_sentiment: float = Field(0.0, ge=-1.0, le=1.0)
    x_mentions: int = Field(0, ge=0)
    news_sentiment: float = Field(0.0, ge=-1.0, le=1.0)
    news_article_count: int = Field(0, ge=0)
    polymarket_probability: float | None = Field(None, ge=0.0, le=1.0)
    aggregated_score: float = Field(0.0, ge=-1.0, le=1.0)
    aggregated_confidence: float = Field(0.0, ge=0.0, le=1.0)
    fetched_at: datetime

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class FredIndicator(BaseModel):
    ticker_symbol: str = Field("MARKET", min_length=1, max_length=16)
    indicator_name: str
    series_id: str
    value: float
    unit: str
    last_updated: datetime
    frequency: str = "M"

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class FearGreedSignal(BaseModel):
    ticker_symbol: str = Field("MARKET", min_length=1, max_length=16)
    score: int = Field(..., ge=0, le=100)
    rating: str
    created_utc: datetime

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class OptionsSignal(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    option_type: str
    strike: float
    expiration: str
    volume: int = Field(..., ge=0)
    open_interest: int = Field(..., ge=0)
    vol_oi_ratio: float = Field(..., ge=0)
    last_price: float
    premium: float = Field(..., ge=0)
    created_utc: datetime

    @field_validator("ticker_symbol")
    @classmethod
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper()


class ExtendedHoursQuote(BaseModel):
    ticker_symbol: str = Field(..., min_length=1, max_length=16)
    regular_price: float | None = None
    previous_close: float | None = None
    pre_market_price: float | None = None
    pre_market_change_pct: float | None = None
    post_market_price: float | None = None
    post_market_change_pct: float | None = None
    market_state: str = "closed"
    created_utc: datetime

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
    stocktwits_score: float = Field(0.0, ge=0.0, le=20.0)
    insider_score: float = Field(0.0, ge=0.0, le=20.0)
    trends_score: float = Field(0.0, ge=0.0, le=15.0)
    earnings_score: float = Field(0.0, ge=0.0, le=15.0)
    sec_score: float = Field(0.0, ge=0.0, le=25.0)
    news_score: float = Field(0.0, ge=0.0, le=20.0)
    technical_score: float = Field(0.0, ge=0.0, le=25.0)
    alpaca_news_score: float = Field(0.0, ge=0.0, le=20.0)
    hackernews_score: float = Field(0.0, ge=0.0, le=15.0)
    telegram_score: float = Field(0.0, ge=0.0, le=20.0)
    bluesky_score: float = Field(0.0, ge=0.0, le=20.0)
    youtube_score: float = Field(0.0, ge=0.0, le=15.0)
    fred_score: float = Field(0.0, ge=0.0, le=15.0)
    fear_greed_score: float = Field(0.0, ge=0.0, le=10.0)
    options_score: float = Field(0.0, ge=0.0, le=20.0)
    twelve_data_score: float = Field(0.0, ge=0.0, le=15.0)
    fmp_score: float = Field(0.0, ge=0.0, le=15.0)
    finra_score: float = Field(0.0, ge=0.0, le=15.0)
    keyvex_score: float = Field(0.0, ge=0.0, le=15.0)
    adanos_score: float = Field(0.0, ge=0.0, le=15.0)
    total_score: float = Field(0.0, ge=0.0, le=400.0)
    classification: GemClassification = GemClassification.DISCARD
    source_count: int = Field(0, ge=0, le=23)
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
            self.reddit_score
            + self.discord_score
            + self.stocktwits_score
            + self.insider_score
            + self.trends_score
            + self.earnings_score
            + self.sec_score
            + self.news_score
            + self.technical_score
            + self.alpaca_news_score
            + self.hackernews_score
            + self.telegram_score
            + self.bluesky_score
            + self.youtube_score
            + self.fred_score
            + self.fear_greed_score
            + self.options_score
            + self.twelve_data_score
            + self.fmp_score
            + self.finra_score
            + self.keyvex_score
            + self.adanos_score,
            2,
        )
        if self.total_score >= 50:
            self.classification = GemClassification.STRONG
        elif self.total_score >= 35:
            self.classification = GemClassification.POTENTIAL
        elif self.total_score >= 25:
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
