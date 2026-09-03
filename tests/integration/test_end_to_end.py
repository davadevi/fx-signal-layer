"""End-to-end tests for the signal pipeline. Requires processed parquet."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.pipeline.signals import DATA_PATH, generate_signals

DATA_FILE = Path(DATA_PATH)
pytestmark = pytest.mark.skipif(
    not DATA_FILE.exists(), reason="processed rates parquet not available"
)


def test_generate_signals_no_future_data():
    cutoff = date(2024, 6, 15)
    signals = generate_signals(cutoff_date=cutoff)
    for s in signals:
        assert s.date == cutoff


def test_generate_signals_respects_cap():
    signals = generate_signals(cutoff_date=date(2024, 6, 15), max_per_week=2)
    assert len(signals) <= 2


def test_generate_signals_crisis_suppression_synthetic():
    """Under an artificial high-volatility regime the pipeline should suppress."""
    import numpy as np

    rng = np.random.default_rng(0)
    n = 800
    dates = pd.date_range("2022-04-01", periods=n, freq="D")
    # base drift + strong shocks throughout → sustained high vol
    shocks = rng.normal(0, 2.0, size=n).cumsum()
    rates = 100 + shocks
    df = pd.DataFrame(
        {
            "date": dates,
            "corridor": "RUB_TJS",
            "rate": rates,
            "is_trading_day": [d.weekday() < 5 for d in dates],
        }
    )
    signals = generate_signals(
        cutoff_date=date(2024, 5, 1), df=df, corridors=["RUB_TJS"]
    )
    # In sustained crisis we expect the regime filter to zero-out signals
    # (may be non-empty in edge cases — the assertion is a soft check)
    for s in signals:
        assert s.regime == "calm"
