import pandas as pd

from stradegy.engine.strategy.base import BaseStrategy, Signal
from stradegy.engine.strategy.earnings_momentum import EarningsMomentumStrategy
from stradegy.engine.strategy.mean_reversion import MeanReversionStrategy
from stradegy.engine.strategy.momentum_breakout import MomentumBreakoutStrategy


class EnsembleStrategy(BaseStrategy):
    def __init__(
        self,
        mean_reversion_weight: float = 0.33,
        momentum_weight: float = 0.33,
        earnings_weight: float = 0.34,
    ):
        super().__init__("Ensemble")
        self.mean_reversion = MeanReversionStrategy()
        self.momentum = MomentumBreakoutStrategy()
        self.earnings = EarningsMomentumStrategy()
        self.weights = {
            "MeanReversion": mean_reversion_weight,
            "MomentumBreakout": momentum_weight,
            "EarningsMomentum": earnings_weight,
        }
        self.min_confidence = 0.5
        self.min_agreement = 2

    def generate_signals(self, df: pd.DataFrame, ticker: str) -> list[Signal]:
        mr_signals = {s.date: s for s in self.mean_reversion.generate_signals(df, ticker)}
        mom_signals = {s.date: s for s in self.momentum.generate_signals(df, ticker)}
        earn_signals = {s.date: s for s in self.earnings.generate_signals(df, ticker)}

        all_dates = set(mr_signals.keys()) | set(mom_signals.keys()) | set(earn_signals.keys())
        ensemble_signals = []

        for d in sorted(all_dates):
            votes = {"buy": 0, "sell": 0, "hold": 0}
            confidences = {"buy": [], "sell": []}

            for strategy_name, signals in [
                ("MeanReversion", mr_signals),
                ("MomentumBreakout", mom_signals),
                ("EarningsMomentum", earn_signals),
            ]:
                if d in signals:
                    action = signals[d].action
                    weight = self.weights[strategy_name]
                    votes[action] += weight
                    if action in confidences:
                        confidences[action].append(signals[d].confidence * weight)

            if votes["buy"] >= self.min_agreement and len(confidences["buy"]) > 0:
                avg_conf = sum(confidences["buy"]) / len(confidences["buy"])
                if avg_conf >= self.min_confidence:
                    price = mr_signals.get(d, mom_signals.get(d, earn_signals.get(d))).price
                    ensemble_signals.append(self._create_signal(
                        ticker, pd.Timestamp(d), "buy", price,
                        confidence=avg_conf,
                        metadata={"votes": votes, "consensus": "buy"},
                    ))
            elif votes["sell"] >= self.min_agreement and len(confidences["sell"]) > 0:
                avg_conf = sum(confidences["sell"]) / len(confidences["sell"])
                if avg_conf >= self.min_confidence:
                    price = mr_signals.get(d, mom_signals.get(d, earn_signals.get(d))).price
                    ensemble_signals.append(self._create_signal(
                        ticker, pd.Timestamp(d), "sell", price,
                        confidence=avg_conf,
                        metadata={"votes": votes, "consensus": "sell"},
                    ))

        return ensemble_signals
