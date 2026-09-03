"""Log-return percentile indicator.

Ranks N-day log-returns (not absolute rate levels) in a rolling window.
Log-returns of I(1) series are I(0) — stationary — making percentile rank valid.

Signal fires when log_return_Nd is in the bottom P-th percentile of the past window:
  - log_ret < 0 (rate fell) means RUB strengthened = favorable for sender
  - In bottom 20% = RUB strengthened MORE than usual in recent history
  - Optional confirmation: rate has been rising for K days (reversal confirmed)

Score range: [0, 1]. Signal fires when score < threshold.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from src.indicators.base import BaseIndicator


class LogReturnPercentileIndicator(BaseIndicator):
    """Percentile rank of N-day log-returns in a rolling window."""

    name = "log_return_percentile"

    def __init__(
        self,
        return_window: int = 5,
        rank_window: int = 60,
        threshold: float = 0.20,
        confirm_days: int = 0,
    ) -> None:
        self.return_window = return_window
        self.rank_window = rank_window
        self.threshold = threshold
        self.confirm_days = confirm_days

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        filtered = self._filter(df, corridor, cutoff_date)
        if filtered.empty:
            return pd.Series(dtype=float, name="log_return_pct_rank")

        td = (
            filtered[filtered["is_trading_day"]]
            .sort_values("date")
            .set_index("date")
        )

        # Log-return over return_window trading days
        log_ret = np.log(td["rate"]).diff(self.return_window)

        # Percentile rank in rolling rank_window: fraction of prior returns
        # strictly less than today's return.
        min_periods = max(2, self.rank_window // 4)
        pct_rank = log_ret.rolling(self.rank_window, min_periods=min_periods).apply(
            lambda x: (x[:-1] < x[-1]).sum() / max(len(x) - 1, 1),
            raw=True,
        )

        # Optional reversal confirmation: rate rising for confirm_days consecutive
        # trading days (suggests the down-move has already reversed).
        if self.confirm_days > 0:
            rising = (td["rate"].diff() > 0).rolling(self.confirm_days).sum() == self.confirm_days
            pct_rank = pct_rank.where(rising, other=float("nan"))

        # Reindex to full daily calendar and forward-fill for weekends
        full_index = pd.date_range(
            start=filtered["date"].min(),
            end=filtered["date"].max(),
            freq="D",
        )
        return pct_rank.reindex(full_index).ffill().rename("log_return_pct_rank")

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
