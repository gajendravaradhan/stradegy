import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field, field_validator


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


class OptionsScanner:
    PREMIUM_THRESHOLD: float = 25000.0
    VOL_OI_RATIO_THRESHOLD: float = 3.0

    def __init__(self):
        self._yf = None
        try:
            import yfinance as yf

            self._yf = yf
            logger.info("Options scanner initialized (yfinance)")
        except ImportError:
            logger.warning("yfinance not installed — options scanner will return empty results")
        except Exception as e:
            logger.warning(f"Options scanner init failed: {e}")

    def _ensure_lib(self) -> bool:
        return self._yf is not None

    def _fetch_options_chain(self, ticker: str):
        try:
            stock = self._yf.Ticker(ticker)
            expirations = stock.options
            if not expirations:
                return []

            now = datetime.now(timezone.utc)
            signals = []

            for exp_date in expirations[:4]:
                try:
                    chain = stock.option_chain(exp_date)
                except Exception:
                    continue

                calls = chain.calls if chain.calls is not None else []
                puts = chain.puts if chain.puts is not None else []

                for opt_type, options in [("CALL", calls), ("PUT", puts)]:
                    if options is None or options.empty:
                        continue
                    for _, row in options.iterrows():
                        try:
                            volume = int(row.get("volume", 0))
                            oi = int(row.get("openInterest", 0))
                            last_price = float(row.get("lastPrice", 0))
                            strike = float(row.get("strike", 0))

                            if oi == 0 or volume == 0:
                                continue

                            vol_oi_ratio = volume / oi
                            premium = volume * last_price * 100

                            if vol_oi_ratio >= self.VOL_OI_RATIO_THRESHOLD and premium >= self.PREMIUM_THRESHOLD:
                                signal = OptionsSignal(
                                    ticker_symbol=ticker,
                                    option_type=opt_type,
                                    strike=strike,
                                    expiration=exp_date,
                                    volume=volume,
                                    open_interest=oi,
                                    vol_oi_ratio=round(vol_oi_ratio, 2),
                                    last_price=round(last_price, 4),
                                    premium=round(premium, 2),
                                    created_utc=now,
                                )
                                signals.append(signal)
                        except Exception:
                            continue

            return signals
        except Exception as e:
            logger.warning(f"Options chain error for {ticker}: {e}")
            return []

    async def scan_hot(self, limit: int = 50) -> list[OptionsSignal]:
        if not self._ensure_lib():
            return []
        logger.info("scan_hot not supported for options scanner — use scan_ticker with a ticker list")
        return []

    async def scan_ticker(self, ticker: str, limit: int = 50) -> list[OptionsSignal]:
        if not self._ensure_lib():
            return []

        try:
            signals = await asyncio.to_thread(self._fetch_options_chain, ticker)
            if signals:
                logger.info(f"Options scan for {ticker}: {len(signals)} unusual activity signals")
            return signals
        except Exception as e:
            logger.warning(f"Options scan error for {ticker}: {e}")
            return []

    async def scan_tickers(self, tickers: list[str], limit: int = 50) -> list[OptionsSignal]:
        if not self._ensure_lib():
            return []

        all_signals: list[OptionsSignal] = []
        for ticker in tickers:
            signals = await self.scan_ticker(ticker, limit)
            all_signals.extend(signals)
            await asyncio.sleep(0.5)

        logger.info(f"Options batch scan: {len(all_signals)} signals across {len(tickers)} tickers")
        return all_signals

    async def close(self):
        pass
