"""Percentile rank indicator — primary signal.

Score in [0, 1]: fraction of PREVIOUS trading days in the rolling window where
the rate was LOWER than today. Low score = today's rate is among the lowest in
the window (favorable for sender). Signal fires when score < threshold.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.indicators.base import BaseIndicator


class PercentileRankIndicator(BaseIndicator):
    name = "percentile_rank"

    def __init__(self, window: int = 30, threshold: float = 0.20) -> None:
        self.window = window
        self.threshold = threshold

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        filtered = self._filter(df, corridor, cutoff_date)
        td = filtered[filtered["is_trading_day"]].sort_values("date").set_index("date")
        pct_rank = td["rate"].rolling(
            self.window, min_periods=max(1, self.window // 2)
        ).apply(
            lambda x: (x < x.iloc[-1]).sum() / (len(x) - 1) if len(x) > 1 else 0.5,
            raw=False,
        )
        if filtered.empty:
            return pd.Series(dtype=float, name="percentile_rank")
        full_index = pd.date_range(
            start=filtered["date"].min(), end=filtered["date"].max(), freq="D"
        )
        return pct_rank.reindex(full_index).ffill().rename("percentile_rank")

    def get_signal(
        self,
        df: pd.DataFrame,
        corridor: str,
        cutoff_date: date,
        threshold: float | None = None,
    ) -> bool:
        t = threshold if threshold is not None else self.threshold
        scores = self.compute(df, corridor, cutoff_date)
        key = pd.Timestamp(cutoff_date)
        if key not in scores.index or pd.isna(scores[key]):
            return False
        return bool(scores[key] < t)
