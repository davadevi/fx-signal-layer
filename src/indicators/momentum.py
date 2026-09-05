"""Momentum indicator — expected negative result per research (trend continues).

Score in [0, 1]: rolling percentile rank of pct change over `lookback_days`
trading days. Documented here so backtest can confirm the null hypothesis.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.indicators.base import BaseIndicator


class MomentumIndicator(BaseIndicator):
    name = "momentum"

    def __init__(self, lookback_days: int = 5, threshold: float = 0.60) -> None:
        self.lookback_days = lookback_days
        self.threshold = threshold

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        filtered = self._filter(df, corridor, cutoff_date)
        td = filtered[filtered["is_trading_day"]].sort_values("date").set_index("date")
        raw_momentum = td["rate"].pct_change(self.lookback_days)
        window = 60
        pct_rank = raw_momentum.rolling(window, min_periods=window // 4).apply(
            lambda x: (x < x.iloc[-1]).sum() / (len(x) - 1) if len(x) > 1 else 0.5,
            raw=False,
        )
        if filtered.empty:
            return pd.Series(dtype=float, name="momentum")
        full_index = pd.date_range(
            start=filtered["date"].min(), end=filtered["date"].max(), freq="D"
        )
        return pct_rank.reindex(full_index).ffill().rename("momentum")
