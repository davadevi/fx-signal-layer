"""Volatility regime filter — suppress signals in crisis periods.

Score: 1.0 = calm (signals allowed), 0.0 = crisis (suppress).
Crisis when realized vol > 85th percentile of vol over past year.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from src.indicators.base import BaseIndicator


class VolatilityRegimeFilter(BaseIndicator):
    name = "volatility_regime"

    def __init__(
        self,
        vol_window: int = 30,
        pct_window: int = 252,
        crisis_pct: float = 0.85,
    ) -> None:
        self.vol_window = vol_window
        self.pct_window = pct_window
        self.crisis_pct = crisis_pct

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        filtered = self._filter(df, corridor, cutoff_date)
        td = filtered[filtered["is_trading_day"]].sort_values("date").set_index("date")
        log_ret = np.log(td["rate"]).diff()
        realized_vol = log_ret.rolling(
            self.vol_window, min_periods=self.vol_window // 2
        ).std() * np.sqrt(252)
        vol_pct_threshold = realized_vol.rolling(
            self.pct_window, min_periods=self.pct_window // 4
        ).quantile(self.crisis_pct)
        regime = (realized_vol <= vol_pct_threshold).astype(float)
        if filtered.empty:
            return pd.Series(dtype=float, name="volatility_regime")
        full_index = pd.date_range(
            start=filtered["date"].min(), end=filtered["date"].max(), freq="D"
        )
        return regime.reindex(full_index).ffill().fillna(1.0).rename("volatility_regime")

    def is_calm(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> bool:
        scores = self.compute(df, corridor, cutoff_date)
        key = pd.Timestamp(cutoff_date)
        if key not in scores.index:
            return True
        return bool(scores[key] >= 0.5)
