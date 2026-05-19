import asyncio
from datetime import date
from pathlib import Path

from loguru import logger

DEFAULT_UNIVERSE = sorted(set([
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "ORCL", "AMD",
    "CRM", "ADBE", "INTC", "IBM", "QCOM", "TXN", "NOW", "UBER", "SNOW", "ZM",
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "C", "AXP", "PNC", "USB",
    "TFC", "COF", "SCHW", "BK", "STT", "SPGI", "MCO", "ICE", "CME", "NDAQ",
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY",
    "AMGN", "GILD", "VRTX", "REGN", "BIIB", "ISRG", "SYK", "ZTS", "CVS", "CI",
    "WMT", "COST", "HD", "LOW", "TGT", "NKE", "MCD", "SBUX", "YUM", "DPZ",
    "CMG", "DRI", "MAR", "HLT", "BKNG", "ABNB", "LVS", "MGM", "CZR", "WYNN",
    "GE", "HON", "CAT", "BA", "UPS", "FDX", "LMT", "RTX", "NOC", "GD",
    "DE", "ITW", "EMR", "ETN", "ROK", "AME", "PH", "SWK", "IR", "DOV",
    "XOM", "CVX", "COP", "EOG", "MPC", "PSX", "VLO", "OXY", "DVN", "FANG",
    "MRO", "HES", "APA", "MUR", "CLR", "WMB", "KMI", "EPD", "ET",
    "LIN", "APD", "SHW", "FCX", "NEM", "DOW", "DD", "PPG", "ECL", "ALB",
    "CF", "MOS", "NUE", "STLD", "RS", "MT", "SCCO", "TECK", "VALE", "BHP",
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "FE",
    "PEG", "ETR", "WEC", "AWK", "CMS", "AEE", "CNP", "NI", "NRG", "AES",
    "AMT", "PLD", "CCI", "EQIX", "PSA", "O", "SPG", "WELL", "AVB", "EQR",
    "UDR", "ESS", "AIV", "CPT", "MAA", "IRT", "NXRT", "ROIC", "EXR", "LSI",
    "RCKT", "TMDX", "INSM", "ARWR", "SRPT", "CRSP", "NTLA", "EDIT", "BEAM", "DNA",
    "PLTR", "SOFI", "AFRM", "HOOD", "RIVN", "LCID", "FSR", "GOEV", "CANO", "CLOV",
    "STEM", "CHPT", "BLNK", "EVGO", "SPWR", "ENPH", "SEDG", "RUN", "NOVA", "CSIQ",
]))


class TickerUniverse:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path("data")
        self.custom_file = self.data_dir / "custom_tickers.txt"
        self.watched_file = self.data_dir / "watched_tickers.txt"
        self._universe: list[str] = []
        self._watched: list[str] = []
        self._last_update: date | None = None

    def get_default_universe(self) -> list[str]:
        return DEFAULT_UNIVERSE.copy()

    def load_custom_tickers(self) -> list[str]:
        if not self.custom_file.exists():
            return []
        content = self.custom_file.read_text().strip()
        if not content:
            return []
        return [t.strip().upper() for t in content.splitlines() if t.strip()]

    def save_custom_tickers(self, tickers: list[str]):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.custom_file.write_text("\n".join(sorted(set(t.upper() for t in tickers))))

    def add_custom_ticker(self, symbol: str):
        custom = set(self.load_custom_tickers())
        custom.add(symbol.upper())
        self.save_custom_tickers(sorted(custom))

    def remove_custom_ticker(self, symbol: str):
        custom = set(self.load_custom_tickers())
        custom.discard(symbol.upper())
        self.save_custom_tickers(sorted(custom))

    def get_full_universe(self) -> list[str]:
        default = set(self.get_default_universe())
        custom = set(self.load_custom_tickers())
        return sorted(default | custom)

    def get_active_universe(self) -> list[str]:
        return self.get_full_universe()

    def load_watched_tickers(self) -> list[str]:
        if not self.watched_file.exists():
            return []
        content = self.watched_file.read_text().strip()
        if not content:
            return []
        return [t.strip().upper() for t in content.splitlines() if t.strip()]

    def save_watched_tickers(self, tickers: list[str]):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.watched_file.write_text("\n".join(sorted(set(t.upper() for t in tickers))))

    def add_watched_ticker(self, symbol: str):
        watched = set(self.load_watched_tickers())
        watched.add(symbol.upper())
        self.save_watched_tickers(sorted(watched))

    def remove_watched_ticker(self, symbol: str):
        watched = set(self.load_watched_tickers())
        watched.discard(symbol.upper())
        self.save_watched_tickers(sorted(watched))

    def get_watched_tickers(self) -> list[str]:
        return self.load_watched_tickers()

    def is_in_universe(self, symbol: str) -> bool:
        return symbol.upper() in self.get_full_universe()

    async def seed_tickers_to_db(self, store) -> int:
        universe = self.get_full_universe()
        count = 0
        for symbol in universe:
            existing = await store.get_ticker(symbol)
            if not existing:
                await store.save_ticker(
                    symbol=symbol,
                    name=None,
                    sector=None,
                    is_active=True,
                    is_watched=symbol in self.load_watched_tickers(),
                    source="default_universe",
                )
                count += 1
        logger.info(f"Seeded {count} new tickers to database")
        return count
