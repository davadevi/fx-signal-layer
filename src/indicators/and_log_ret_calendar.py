"""AND-combination indicator: log_return_percentile(confirm=0) AND calendar favorable.

Delegates to sub-indicators (each calls its own `_filter()`); this class does
not touch raw df directly, so no-lookahead is inherited from sub-indicators.

Score = log_ret score on favorable calendar days, NaN otherwise.
Signal fires when score < threshold (= log_ret score < 0.20).
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.indicators.base import BaseIndicator
from src.indicators.calendar_seasonality import CalendarSeasonalityIndicator
from src.indicators.log_return_percentile import LogReturnPercentileIndicator


class AndLogRetCalendarIndicator(BaseIndicator):
    """AND: log_return_percentile(confirm=0) fires AND calendar is favorable."""

    name = "log_ret_and_calendar"

    def __init__(
        self,
        return_window: int = 5,
        rank_window: int = 60,
        threshold: float = 0.20,
    ) -> None:
        self.return_window = return_window
        self.rank_window = rank_window
        self.threshold = threshold

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        log_ret_ind = LogReturnPercentileIndicator(
            return_window=self.return_window,
            rank_window=self.rank_window,
            threshold=self.threshold,
            confirm_days=0,
        )
        cal_ind = CalendarSeasonalityIndicator(threshold=0.5)

        log_scores = log_ret_ind.compute(df, corridor, cutoff_date)
        cal_scores = cal_ind.compute(df, corridor, cutoff_date)

        idx = log_scores.index
        cal_aligned = cal_scores.reindex(idx)

        # AND: keep log_ret score only when calendar is favorable (cal_score < 0.5)
        result = log_scores.where(cal_aligned < 0.5, other=float("nan"))
        return result.rename("log_ret_and_calendar")

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
