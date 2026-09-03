"""Bollinger Z-score indicator.

Z-score of rate vs its rolling mean, in units of rolling std:
  z = (rate - MA_N) / STD_N

Z is I(0) (deviation from mean in units of std) — stationary and comparable
across time. When z << 0, the rate is far below its recent mean → RUB has
strengthened unusually much = favorable for the sender.

Score range: raw Z (unbounded, typically in [-3, 3]).
Signal fires when score < threshold (default -1.5).
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.indicators.base import BaseIndicator


class BollingerZScoreIndicator(BaseIndicator):
    """Rolling Z-score of rate vs its own moving average."""

    name = "bollinger_zscore"

    def __init__(
        self,
        ma_window: int = 20,
        std_window: int = 20,
        threshold: float = -1.5,
        confirm_days: int = 1,
    ) -> None:
        self.ma_window = ma_window
        self.std_window = std_window
        self.threshold = threshold
        self.confirm_days = confirm_days

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        filtered = self._filter(df, corridor, cutoff_date)
        if filtered.empty:
            return pd.Series(dtype=float, name="bollinger_z")

        td = (
            filtered[filtered["is_trading_day"]]
            .sort_values("date")
            .set_index("date")
        )

        ma = td["rate"].rolling(self.ma_window, min_periods=self.ma_window // 2).mean()
        std = td["rate"].rolling(self.std_window, min_periods=self.std_window // 2).std()
        z = (td["rate"] - ma) / std

        # Optional confirmation: rate rising (reversal already started)
        # for confirm_days consecutive trading days.
        if self.confirm_days > 0:
            rising = (td["rate"].diff() > 0).rolling(self.confirm_days).sum() == self.confirm_days
            z = z.where(rising, other=float("nan"))

        full_index = pd.date_range(
            start=filtered["date"].min(),
            end=filtered["date"].max(),
            freq="D",
        )
        return z.reindex(full_index).ffill().rename("bollinger_z")

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
