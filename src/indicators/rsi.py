"""RSI confirming filter (Wilder smoothing, trading days only).

Score = RSI/100 in [0, 1]. Signal fires when score <= threshold (RSI oversold).
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from src.indicators.base import BaseIndicator


class RSIFilter(BaseIndicator):
    name = "rsi_filter"

    def __init__(self, period: int = 14, threshold: float = 35.0) -> None:
        self.period = period
        self.threshold = threshold

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        filtered = self._filter(df, corridor, cutoff_date)
        td = filtered[filtered["is_trading_day"]].sort_values("date").set_index("date")
        delta = td["rate"].diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(
            alpha=1 / self.period, min_periods=self.period, adjust=False
        ).mean()
        avg_loss = loss.ewm(
            alpha=1 / self.period, min_periods=self.period, adjust=False
        ).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        score = rsi / 100.0
        if filtered.empty:
            return pd.Series(dtype=float, name="rsi_score")
        full_index = pd.date_range(
            start=filtered["date"].min(), end=filtered["date"].max(), freq="D"
        )
        return score.reindex(full_index).ffill().rename("rsi_score")

    def get_signal(
        self,
        df: pd.DataFrame,
        corridor: str,
        cutoff_date: date,
        threshold: float | None = None,
    ) -> bool:
        t = threshold if threshold is not None else self.threshold / 100.0
        scores = self.compute(df, corridor, cutoff_date)
        key = pd.Timestamp(cutoff_date)
        if key not in scores.index or pd.isna(scores[key]):
            return False
        return bool(scores[key] <= t)
