from dataclasses import dataclass
from datetime import date
from typing import Literal

import pandas as pd

from stradegy.engine.strategy.indicators import TechnicalIndicators


@dataclass
class Signal:
    ticker: str
    date: date
    action: Literal["buy", "sell", "hold"]
    price: float
    confidence: float = 0.0
    strategy: str = ""
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseStrategy:
    def __init__(self, name: str):
        self.name = name

    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        raise NotImplementedError

    def _create_signal(self, ticker: str, idx: pd.Timestamp, action: str, price: float, confidence: float, metadata: dict) -> Signal:
        return Signal(
            ticker=ticker,
            date=idx.date(),
            action=action,
            price=price,
            confidence=confidence,
            strategy=self.name,
            metadata=metadata,
        )
