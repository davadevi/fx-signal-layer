"""Backtest metrics: hit rate, lift, clustering, cost of waiting.

All hit-rate metrics use the forward-only convention:
    hit = rate[t+h] >= rate[t]
Lower rate = favorable for sender. A signal on day t is a "hit" if the rate
did not drop further within the next h days (client was right to transfer now).
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


def _to_timestamp(d: date) -> pd.Timestamp:
    return pd.Timestamp(d)


def _forward_hits(
    days: list[pd.Timestamp],
    rates: pd.Series,
    h: int,
) -> tuple[int, int]:
    """Return (n_hits, n_eligible) using calendar-day offset for t+h.

    rates must be a full daily-indexed series (weekends forward-filled)
    so that rate[t+h] is defined for every calendar t.
    """
    if not len(days) or rates.empty:
        return 0, 0
    hits = 0
    eligible = 0
    max_date = rates.index.max()
    for t in days:
        t_plus = t + pd.Timedelta(days=h)
        if t not in rates.index or t_plus > max_date:
            continue
        if t_plus not in rates.index:
            continue
        r_t = rates.loc[t]
        r_h = rates.loc[t_plus]
        if pd.isna(r_t) or pd.isna(r_h):
            continue
        eligible += 1
        if r_h >= r_t:
            hits += 1
    return hits, eligible


def hit_rate_at_h(
    signals: list[date],
    rates: pd.Series,
    h: int,
) -> float:
    """Fraction of signals where rate[t+h] >= rate[t]. NaN if no eligible."""
    days = [_to_timestamp(d) for d in signals]
    hits, eligible = _forward_hits(days, rates, h)
    if eligible == 0:
        return float("nan")
    return hits / eligible


def base_rate_at_h(
    trading_days: pd.DatetimeIndex,
    rates: pd.Series,
    h: int,
) -> float:
    """Fraction of random trading days where rate[t+h] >= rate[t]."""
    days = list(trading_days)
    hits, eligible = _forward_hits(days, rates, h)
    if eligible == 0:
        return float("nan")
    return hits / eligible


def lift_over_random(
    signals: list[date],
    rates: pd.Series,
    trading_days: pd.DatetimeIndex,
    h: int,
) -> float:
    """hit_rate_at_h / base_rate_at_h. NaN if base rate is 0 or undefined."""
    base = base_rate_at_h(trading_days, rates, h)
    hit = hit_rate_at_h(signals, rates, h)
    if not base or np.isnan(base) or np.isnan(hit):
        return float("nan")
    return hit / base


def clustering_score(signals: list[date]) -> float:
    """Coefficient of variation of inter-signal gaps.

    0 = perfectly evenly spread. Higher = more clustered / irregular.
    Returns NaN if fewer than 3 signals (need at least 2 gaps).
    """
    if len(signals) < 3:
        return float("nan")
    sorted_days = sorted(signals)
    gaps = np.array(
        [(sorted_days[i + 1] - sorted_days[i]).days for i in range(len(sorted_days) - 1)],
        dtype=float,
    )
    if gaps.mean() == 0:
        return float("nan")
    return float(gaps.std(ddof=0) / gaps.mean())


def cost_of_waiting_bps(
    signals: list[date],
    rates: pd.Series,
    h_fast: int = 1,
    h_slow: int = 5,
) -> float:
    """Expected basis points difference from waiting h_slow instead of h_fast.

    Positive = waiting cost the client money (rate got worse).
    Negative = waiting was beneficial.
    """
    if not len(signals) or rates.empty:
        return float("nan")
    diffs = []
    max_date = rates.index.max()
    for d in signals:
        t = _to_timestamp(d)
        t_fast = t + pd.Timedelta(days=h_fast)
        t_slow = t + pd.Timedelta(days=h_slow)
        if t not in rates.index or t_slow > max_date:
            continue
        r_fast = rates.get(t_fast, np.nan)
        r_slow = rates.get(t_slow, np.nan)
        if pd.isna(r_fast) or pd.isna(r_slow) or r_fast == 0:
            continue
        diffs.append((r_slow - r_fast) / r_fast * 10_000)
    if not diffs:
        return float("nan")
    return float(np.mean(diffs))


def apply_cooldown(signal_days: list[date], cooldown_days: int = 3) -> list[date]:
    """Enforce a minimum gap between consecutive signals. Keeps the earliest."""
    if not signal_days:
        return []
    sorted_days = sorted(signal_days)
    kept: list[date] = [sorted_days[0]]
    for d in sorted_days[1:]:
        if (d - kept[-1]).days >= cooldown_days:
            kept.append(d)
    return kept
