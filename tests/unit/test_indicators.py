"""Unit tests for indicators: no-lookahead, score ranges, signal semantics."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.indicators import (
    LogReturnPercentileIndicator,
    MomentumIndicator,
    PercentileRankIndicator,
    RSIFilter,
    VolatilityRegimeFilter,
)


def make_test_df(
    n_days: int = 300,
    corridor: str = "RUB_TJS",
    rates: np.ndarray | None = None,
) -> pd.DataFrame:
    dates = pd.date_range("2022-04-01", periods=n_days, freq="D")
    if rates is None:
        rates = np.arange(n_days, dtype=float) + 10.0
    is_trading = [d.weekday() < 5 for d in dates]
    return pd.DataFrame(
        {
            "date": dates,
            "corridor": corridor,
            "rate": rates,
            "is_trading_day": is_trading,
        }
    )


# ---- No-lookahead tests ------------------------------------------------------

@pytest.mark.parametrize(
    "ind_cls",
    [
        PercentileRankIndicator,
        RSIFilter,
        VolatilityRegimeFilter,
        MomentumIndicator,
        LogReturnPercentileIndicator,
    ],
)
def test_no_lookahead(ind_cls):
    df = make_test_df(300)
    cutoff = date(2022, 8, 1)
    ind = ind_cls()
    scores = ind.compute(df, "RUB_TJS", cutoff)
    key = pd.Timestamp(cutoff)
    assert (scores.index <= key).all(), f"{ind_cls.__name__} leaked future data"


# ---- Score ranges ------------------------------------------------------------

def test_percentile_score_in_unit_range():
    df = make_test_df(200)
    ind = PercentileRankIndicator()
    scores = ind.compute(df, "RUB_TJS", date(2022, 9, 1)).dropna()
    assert ((scores >= 0) & (scores <= 1)).all()


def test_rsi_score_in_unit_range():
    df = make_test_df(200)
    ind = RSIFilter()
    scores = ind.compute(df, "RUB_TJS", date(2022, 9, 1)).dropna()
    assert ((scores >= 0) & (scores <= 1)).all()


def test_regime_score_binary():
    df = make_test_df(500)
    ind = VolatilityRegimeFilter()
    scores = ind.compute(df, "RUB_TJS", date(2023, 7, 1)).dropna()
    assert set(scores.unique()).issubset({0.0, 1.0})


def test_momentum_score_in_unit_range():
    df = make_test_df(300)
    ind = MomentumIndicator()
    scores = ind.compute(df, "RUB_TJS", date(2022, 12, 1)).dropna()
    assert ((scores >= 0) & (scores <= 1)).all()


# ---- Signal semantics --------------------------------------------------------

def test_percentile_fires_when_rate_is_low():
    # Falling rate → today is lowest → percentile ~ 0 → signal fires
    rates = np.linspace(100.0, 50.0, 200)
    df = make_test_df(200, rates=rates)
    ind = PercentileRankIndicator(window=30, threshold=0.20)
    cutoff = date(2022, 9, 1)
    assert ind.get_signal(df, "RUB_TJS", cutoff) is True


def test_percentile_does_not_fire_when_rate_is_high():
    # Rising rate → today is highest → percentile ~ 1 → no signal
    rates = np.linspace(50.0, 100.0, 200)
    df = make_test_df(200, rates=rates)
    ind = PercentileRankIndicator(window=30, threshold=0.20)
    cutoff = date(2022, 9, 1)
    assert ind.get_signal(df, "RUB_TJS", cutoff) is False


def test_rsi_fires_on_downtrend():
    rates = np.linspace(100.0, 50.0, 200)
    df = make_test_df(200, rates=rates)
    ind = RSIFilter(period=14, threshold=35.0)
    cutoff = date(2022, 9, 1)
    assert ind.get_signal(df, "RUB_TJS", cutoff) is True


class TestLogReturnPercentileIndicator:
    def test_no_lookahead(self):
        df = make_test_df(300)
        cutoff = date(2022, 8, 1)
        ind = LogReturnPercentileIndicator()
        scores = ind.compute(df, "RUB_TJS", cutoff)
        key = pd.Timestamp(cutoff)
        assert (scores.index <= key).all()

    def test_scores_in_range(self):
        rng = np.random.default_rng(0)
        rates = 100 + rng.normal(0, 0.3, size=250).cumsum()
        df = make_test_df(250, rates=rates)
        ind = LogReturnPercentileIndicator()
        scores = ind.compute(df, "RUB_TJS", date(2022, 11, 1)).dropna()
        assert ((scores >= 0) & (scores <= 1)).all()

    def test_fires_on_sharp_downmove(self):
        # Flat/noisy rate then a sharp drop → recent log-return is in bottom percentile.
        rng = np.random.default_rng(1)
        base = 100 + rng.normal(0, 0.05, size=200).cumsum()
        drop = np.linspace(base[-1], base[-1] * 0.90, 20)
        rates = np.concatenate([base, drop])
        df = make_test_df(len(rates), rates=rates)
        ind = LogReturnPercentileIndicator(
            return_window=5, rank_window=60, threshold=0.20, confirm_days=0
        )
        cutoff = df["date"].iloc[-1].date()
        assert ind.get_signal(df, "RUB_TJS", cutoff) is True

    def test_confirm_days_suppresses_still_falling(self):
        # Monotone fall → confirm_days=2 requires two rising days, so no signal.
        rates = np.linspace(100.0, 60.0, 250)
        df = make_test_df(250, rates=rates)
        ind = LogReturnPercentileIndicator(
            return_window=5, rank_window=60, threshold=0.50, confirm_days=2
        )
        cutoff = date(2022, 11, 1)
        assert ind.get_signal(df, "RUB_TJS", cutoff) is False


def test_regime_detects_crisis():
    # Calm period followed by high-vol crisis
    rng = np.random.default_rng(42)
    n = 600
    calm = 100 + rng.normal(0, 0.05, size=400).cumsum()
    crisis_shocks = rng.normal(0, 3.0, size=200).cumsum()
    rates = np.concatenate([calm, calm[-1] + crisis_shocks])
    df = make_test_df(n, rates=rates)
    ind = VolatilityRegimeFilter()
    # In crisis window, is_calm should be False at some point
    late_scores = ind.compute(df, "RUB_TJS", date(2023, 11, 1)).dropna()
    assert (late_scores == 0.0).any(), "Crisis regime should be detected"
