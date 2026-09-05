"""Unit tests for backtest metrics."""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from src.backtest.metrics import (
    apply_cooldown,
    base_rate_at_h,
    clustering_score,
    cost_of_waiting_bps,
    hit_rate_at_h,
)


def _make_rates(values: list[float], start="2024-01-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)


def test_hit_rate_all_hits():
    # Rate stays flat: rate[t+h] == rate[t] → hit (>=)
    rates = _make_rates([100.0] * 30)
    signals = [date(2024, 1, 5), date(2024, 1, 10)]
    assert hit_rate_at_h(signals, rates, h=5) == 1.0


def test_hit_rate_no_hits():
    # Rate falls monotonically: rate[t+h] < rate[t] → miss
    rates = _make_rates([100.0 - i for i in range(30)])
    signals = [date(2024, 1, 5), date(2024, 1, 10)]
    assert hit_rate_at_h(signals, rates, h=3) == 0.0


def test_base_rate_only_uses_trading_days():
    # Increasing rate → every day is a "hit" against future
    rates = _make_rates([100.0 + i for i in range(30)])
    trading_days = pd.DatetimeIndex(
        [pd.Timestamp("2024-01-01") + pd.Timedelta(days=i) for i in range(20)]
    )
    br = base_rate_at_h(trading_days, rates, h=3)
    assert br == 1.0


def test_apply_cooldown_enforces_gap():
    days = [
        date(2024, 1, 1),
        date(2024, 1, 2),
        date(2024, 1, 3),  # within 3-day cooldown of Jan 1 → drop
        date(2024, 1, 5),  # >= 3 days after Jan 1 → keep
        date(2024, 1, 6),  # within 3 of Jan 5 → drop
        date(2024, 1, 10),
    ]
    kept = apply_cooldown(days, cooldown_days=3)
    assert kept == [date(2024, 1, 1), date(2024, 1, 5), date(2024, 1, 10)]


def test_clustering_score_evenly_spread_low():
    # 3-day spacing everywhere → CV = 0
    days = [date(2024, 1, 1) + timedelta(days=3 * i) for i in range(10)]
    assert clustering_score(days) == 0.0


def test_clustering_score_clustered_high():
    # Two clusters far apart → high CV
    days = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 3, 1)]
    assert clustering_score(days) > 1.0


def test_cost_of_waiting_positive_when_rate_rises():
    # Rate climbs → waiting costs money
    rates = _make_rates([100.0 + i for i in range(30)])
    signals = [date(2024, 1, 5), date(2024, 1, 8)]
    cow = cost_of_waiting_bps(signals, rates, h_fast=1, h_slow=5)
    assert cow > 0


def test_hit_rate_nan_when_no_eligible():
    rates = _make_rates([100.0] * 5)
    # Signals past the end → no eligible
    signals = [date(2024, 1, 4)]
    assert np.isnan(hit_rate_at_h(signals, rates, h=10))
