"""Calendar seasonality indicator.

Two well-documented calendar effects on RUB / CIS FX corridors:

1. Russian tax period (days 20-28 of each month): exporters sell FX to pay
   RUB-denominated taxes → RUB temporarily strengthens → CIS rates rise
   (favorable for the sender). Applies to ALL corridors.

2. Remittance peak season (July-October): labor migrants from Central Asia
   work spring→fall in Russia and remit heavily in the peak months. Demand
   for TJS/KGS/UZS spikes → CIS rates favorable for the sender.
   Applies to migration corridors only: RUB_TJS, RUB_KGS, RUB_UZS.

Score is BINARY: 0.0 on favorable calendar days, 1.0 otherwise.
Signal fires when score < threshold (default 0.5).
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.indicators.base import BaseIndicator


MIGRATION_CORRIDORS = frozenset({"RUB_TJS", "RUB_KGS", "RUB_UZS"})
REMITTANCE_MONTHS = frozenset({7, 8, 9, 10})
TAX_DAY_START = 20
TAX_DAY_END = 28


class CalendarSeasonalityIndicator(BaseIndicator):
    """Deterministic calendar-driven favorability score."""

    name = "calendar_seasonality"

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold

    def _score_for_date(self, d: pd.Timestamp, corridor: str) -> float:
        day = d.day
        month = d.month

        if TAX_DAY_START <= day <= TAX_DAY_END:
            return 0.0

        if corridor in MIGRATION_CORRIDORS and month in REMITTANCE_MONTHS:
            return 0.0

        return 1.0

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        filtered = self._filter(df, corridor, cutoff_date)
        if filtered.empty:
            return pd.Series(dtype=float, name="calendar_seasonality")

        full_index = pd.date_range(
            start=filtered["date"].min(),
            end=filtered["date"].max(),
            freq="D",
        )
        values = [self._score_for_date(ts, corridor) for ts in full_index]
        return pd.Series(values, index=full_index, name="calendar_seasonality")

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
