"""OR-combination of two LogReturnPercentileIndicator variants.

Wraps strong (confirm=2) and weak (confirm=0) variants into a single indicator
usable by the backtest engine (which takes one indicator at a time).

Score encodes tier:
  < 0.20      -> strong signal (confirm=2 fired)
  0.20-0.40   -> weak signal (confirm=0 fired, confirm=2 did not)
  NaN / >=0.40 -> no signal

Engine fires when score < threshold (0.40).
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.indicators.base import BaseIndicator
from src.indicators.log_return_percentile import LogReturnPercentileIndicator


class CombinedLogReturnIndicator(BaseIndicator):
    """OR-combination: fires when confirm=2 OR confirm=0 fires."""

    name = "log_ret_combined"

    def __init__(self, return_window: int = 5, rank_window: int = 60) -> None:
        self.return_window = return_window
        self.rank_window = rank_window
        self.threshold = 0.40  # engine fires when score < threshold

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        strong = LogReturnPercentileIndicator(
            return_window=self.return_window,
            rank_window=self.rank_window,
            threshold=0.20,
            confirm_days=2,
        )
        weak = LogReturnPercentileIndicator(
            return_window=self.return_window,
            rank_window=self.rank_window,
            threshold=0.20,
            confirm_days=0,
        )
        s_scores = strong.compute(df, corridor, cutoff_date)
        w_scores = weak.compute(df, corridor, cutoff_date)

        idx = s_scores.index.union(w_scores.index)
        result = pd.Series(float("nan"), index=idx)

        s_aligned = s_scores.reindex(idx)
        w_aligned = w_scores.reindex(idx)

        # Where strong fires (< 0.20): keep strong score (range 0..0.20)
        strong_mask = s_aligned < 0.20
        result[strong_mask] = s_aligned[strong_mask]

        # Where only weak fires: remap to 0.20-0.40
        weak_mask = (w_aligned < 0.20) & ~strong_mask.fillna(False)
        result[weak_mask] = 0.20 + w_aligned[weak_mask]

        return result.rename("log_ret_combined")
