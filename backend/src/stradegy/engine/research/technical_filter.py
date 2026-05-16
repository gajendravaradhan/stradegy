from datetime import date, timedelta

import numpy as np
import pandas as pd
import pandas_ta as ta
from loguru import logger

from stradegy.engine.data.store import DataStore
from stradegy.engine.research.models import TechnicalScore


class TechnicalFilter:
    def __init__(self, store: DataStore):
        self.store = store

    async def analyze(self, symbol: str) -> TechnicalScore:
        ohlcv = await self.store.get_ticker_data(
            symbol,
            end_date=date.today(),
            limit=100,
        )

        if not ohlcv or len(ohlcv) < 50:
            logger.warning(f"Insufficient data for {symbol}: {len(ohlcv)} rows")
            return self._empty_score(symbol)

        df = pd.DataFrame(
            [
                {
                    "date": r.date,
                    "open": float(r.open),
                    "high": float(r.high),
                    "low": float(r.low),
                    "close": float(r.close),
                    "volume": r.volume,
                }
                for r in ohlcv
            ]
        )
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)

        current_price = df["close"].iloc[-1]
        current_volume = df["volume"].iloc[-1]

        sma15 = df["close"].rolling(window=15).mean().iloc[-1]
        sma50 = df["close"].rolling(window=50).mean().iloc[-1]
        high_20 = df["close"].rolling(window=20).max().iloc[-1]
        avg_volume_50 = df["volume"].rolling(window=50).mean().iloc[-1]

        price_vs_sma15 = current_price / sma15 if sma15 > 0 else 0
        price_vs_20day_high = current_price / high_20 if high_20 > 0 else 0
        volume_ratio = current_volume / avg_volume_50 if avg_volume_50 > 0 else 0

        rsi_series = ta.rsi(df["close"], length=14)
        rsi_14 = rsi_series.iloc[-1] if rsi_series is not None and not rsi_series.empty else None

        passes_price = current_price > 1.0 and (
            current_price < sma15 or current_price > high_20
        )
        passes_volume = volume_ratio > 1.0
        passes_market_cap = True
        passes_rsi = (
            (rsi_14 is not None and (rsi_14 < 35 or rsi_14 > 50))
            if rsi_14 is not None
            else False
        )

        overall = passes_price and passes_volume and passes_rsi

        return TechnicalScore(
            ticker_symbol=symbol,
            price=round(current_price, 2),
            price_vs_sma15=round(price_vs_sma15, 4),
            price_vs_20day_high=round(price_vs_20day_high, 4),
            volume_vs_50day_avg=round(volume_ratio, 4),
            rsi_14=round(rsi_14, 2) if rsi_14 is not None else None,
            passes_price_filter=passes_price,
            passes_volume_filter=passes_volume,
            passes_market_cap_filter=passes_market_cap,
            passes_rsi_filter=passes_rsi,
            overall_pass=overall,
        )

    def _empty_score(self, symbol: str) -> TechnicalScore:
        return TechnicalScore(
            ticker_symbol=symbol,
            price=0.0,
            price_vs_sma15=0.0,
            price_vs_20day_high=0.0,
            volume_vs_50day_avg=0.0,
            passes_price_filter=False,
            passes_volume_filter=False,
            passes_market_cap_filter=False,
            passes_rsi_filter=False,
            overall_pass=False,
        )
