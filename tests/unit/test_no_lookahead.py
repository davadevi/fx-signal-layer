"""Sanity tests: no indicator must use data after cutoff_date."""
from datetime import date

import pandas as pd
import pytest

from src.indicators.base import BaseIndicator


def make_df(n_days: int = 100) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D")
    return pd.DataFrame({
        "date": dates,
        "corridor": "RUB_TJS",
        "rate_normalized": range(n_days),
        "is_trading_day": True,
    })


class LeakyIndicator(BaseIndicator):
    """Intentionally broken: uses future data."""
    name = "leaky"

    def compute(self, df, corridor, cutoff_date):
        data = df[df["corridor"] == corridor]  # no cutoff filter!
        return data.set_index("date")["rate_normalized"]


class CleanIndicator(BaseIndicator):
    """Correct: respects cutoff_date."""
    name = "clean"

    def compute(self, df, corridor, cutoff_date):
        data = self._filter(df, corridor, cutoff_date)
        return data.set_index("date")["rate_normalized"]


def test_clean_indicator_respects_cutoff():
    df = make_df(100)
    cutoff = pd.Timestamp(date(2020, 3, 10))
    ind = CleanIndicator()
    scores = ind.compute(df, "RUB_TJS", cutoff)
    assert all(d <= cutoff for d in scores.index), "Future dates in scores"


def test_leaky_indicator_violates_cutoff():
    df = make_df(100)
    cutoff = pd.Timestamp(date(2020, 3, 10))
    ind = LeakyIndicator()
    scores = ind.compute(df, "RUB_TJS", cutoff)
    # This should fail — demonstrates why _filter must be used
    assert any(d > cutoff for d in scores.index), "Leaky indicator should have future dates"
