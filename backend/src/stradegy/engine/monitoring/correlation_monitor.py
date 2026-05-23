from datetime import datetime, timezone
from typing import Any

import numpy as np
from loguru import logger

from stradegy.db import async_session
from stradegy.engine.data.store import DataStore


class CorrelationMonitor:
    def __init__(self):
        self.threshold = 0.80
        self.lookback_days = 90

    async def check_drift(self) -> dict[str, Any]:
        alerts = []
        async with async_session() as session:
            store = DataStore(session)
            tickers = await store.get_active_tickers()
            symbols = [t.symbol for t in tickers]
            if len(symbols) < 2:
                return {"alerts": [], "pairs_checked": 0}

            prices = {}
            for sym in symbols:
                try:
                    df = await store.get_ohlcv_dataframe(sym, limit=self.lookback_days)
                    if df is not None and len(df) >= 30:
                        prices[sym] = df["close"].pct_change().dropna().values
                except Exception:
                    continue

            pairs_checked = 0
            sym_list = list(prices.keys())
            for i in range(len(sym_list)):
                for j in range(i + 1, len(sym_list)):
                    s1, s2 = sym_list[i], sym_list[j]
                    v1, v2 = prices[s1], prices[s2]
                    min_len = min(len(v1), len(v2))
                    if min_len < 20:
                        continue
                    corr = np.corrcoef(v1[:min_len], v2[:min_len])[0, 1]
                    pairs_checked += 1
                    if np.isnan(corr):
                        continue
                    if abs(corr) >= self.threshold:
                        alerts.append({
                            "type": "high_correlation",
                            "pair": f"{s1}-{s2}",
                            "correlation": round(float(corr), 3),
                            "message": f"{s1} and {s2} correlation: {corr:.2f} (threshold: {self.threshold})",
                        })

        if alerts:
            logger.warning(f"Correlation drift: {len(alerts)} high-correlation pairs found")
        else:
            logger.info(f"Correlation drift: clean across {pairs_checked} pairs")

        return {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "pairs_checked": pairs_checked,
            "alerts": alerts,
        }
