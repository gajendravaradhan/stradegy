from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Stradegy"
    app_version: str = "0.1.0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8420
    debug: bool = False

    # Trading mode
    paper_trading: bool = True
    autonomy_mode: str = "semi"  # "semi" or "full"

    # Alpaca
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Finnhub
    finnhub_api_key: str = ""

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "stradegy/1.0"

    # Paths
    data_dir: Path = Path("data")
    config_dir: Path = Path("config")
    eval_dir: Path = Path("eval")
    strategies_dir: Path = Path("strategies")

    # Database
    database_url: str = "sqlite+aiosqlite:///data/stradegy.db"

    # Risk parameters
    max_drawdown: float = 0.20
    risk_per_trade: float = 0.03
    max_positions: int = 1
    stop_atr_mult: float = 1.5
    tax_rate_short_term: float = 0.30
    tax_rate_long_term: float = 0.15

    @property
    def alpaca_base_url(self) -> str:
        if self.paper_trading:
            return "https://paper-api.alpaca.markets"
        return "https://api.alpaca.markets"


settings = Settings()
