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

    Hit = pathwise: min(rate[t+1..t+h]) >= rate[t].
    Matches the product definition: rate must not worsen on any day in the window,
    since the client may open the push notification late.
    rates must be a full daily-indexed series (weekends forward-filled).
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
        if pd.isna(r_t):
            continue
        future_slice = rates.loc[t + pd.Timedelta(days=1) : t_plus]
        if future_slice.empty or future_slice.isna().all():
            continue
        eligible += 1
        if float(future_slice.min()) >= r_t:
            hits += 1
    return hits, eligible


def hit_rate_at_h(
    signals: list[date],
    rates: pd.Series,
    h: int,
) -> float:
    """Fraction of signals where min(rate[t+1..t+h]) >= rate[t] (pathwise). NaN if no eligible."""
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


def hit_rate_at_h_below_avg(
    signals: list[date],
    rates: pd.Series,
    h: int,
) -> float:
    """Hit rate using definition B: rate[t] < mean(rate[t+1..t+h]).

    Theoretically sounder for 'was this a good day to transfer':
    client got a rate below the average of the next h days.
    Can only be computed in backtest (requires future data).
    """
    if not signals or rates.empty:
        return float("nan")
    hits = 0
    eligible = 0
    max_date = rates.index.max()
    for d in signals:
        t = _to_timestamp(d)
        if t not in rates.index:
            continue
        if t + pd.Timedelta(days=h) > max_date:
            continue
        future_rates: list[float] = []
        for i in range(1, h + 1):
            fd = t + pd.Timedelta(days=i)
            if fd in rates.index:
                v = rates.loc[fd]
                if not pd.isna(v):
                    future_rates.append(float(v))
        if len(future_rates) < max(1, h // 2):
            continue
        eligible += 1
        if not pd.isna(rates.loc[t]) and rates.loc[t] < np.mean(future_rates):
            hits += 1
    if eligible == 0:
        return float("nan")
    return hits / eligible


def base_rate_at_h_below_avg(
    trading_days: pd.DatetimeIndex,
    rates: pd.Series,
    h: int,
) -> float:
    """Base rate for definition B on random trading days."""
    days = [pd.Timestamp(d) for d in trading_days]
    return hit_rate_at_h_below_avg(days, rates, h)


def lift_over_random_b(
    signals: list[date],
    rates: pd.Series,
    trading_days: pd.DatetimeIndex,
    h: int,
) -> float:
    """Lift using hit definition B (below-average future deal)."""
    base = base_rate_at_h_below_avg(trading_days, rates, h)
    hit = hit_rate_at_h_below_avg(signals, rates, h)
    if not base or np.isnan(base) or np.isnan(hit):
        return float("nan")
    return hit / base


def lift_confidence_interval(
    signals: list[date],
    rates: pd.Series,
    trading_days: pd.DatetimeIndex,
    h: int,
    n_resamples: int = 2000,
    confidence_level: float = 0.95,
    definition: str = "A",
    block_days: int = 90,
) -> tuple[float, float]:
    """Circular block bootstrap CI for lift.

    Jointly resamples signals and trading days in time blocks to account for
    FX autocorrelation, overlapping horizons, and baseline estimation error.
    block_days >= 90 is recommended.
    """
    from numpy.random import default_rng

    rng = default_rng(42)

    if not signals or trading_days.empty or rates.empty:
        return float("nan"), float("nan")

    if definition == "A":
        hit_fn = hit_rate_at_h
        base_fn = base_rate_at_h
    else:
        hit_fn = hit_rate_at_h_below_avg
        base_fn = base_rate_at_h_below_avg

    sig_dates = sorted(signals)
    td_sorted = sorted(trading_days)

    if not sig_dates or not td_sorted:
        return float("nan"), float("nan")

    min_date = min(pd.Timestamp(sig_dates[0]), td_sorted[0])
    max_date = max(pd.Timestamp(sig_dates[-1]), td_sorted[-1])
    total_days = (max_date - min_date).days + 1

    if total_days < block_days:
        return float("nan"), float("nan")

    n_blocks = max(1, round(total_days / block_days))

    sig_set = set(sig_dates)
    td_set = set(td_sorted)

    boot_lifts: list[float] = []
    for _ in range(n_resamples):
        # Sample n_blocks block start offsets (circular)
        starts = rng.integers(0, total_days, size=n_blocks)
        boot_signals: list[date] = []
        boot_td: list[pd.Timestamp] = []
        for start in starts:
            for day_offset in range(block_days):
                d = (min_date + pd.Timedelta(days=int((start + day_offset) % total_days))).date()
                if d in sig_set:
                    boot_signals.append(d)
                td_ts = pd.Timestamp(d)
                if td_ts in td_set:
                    boot_td.append(td_ts)

        if not boot_signals or not boot_td:
            continue
        boot_idx = pd.DatetimeIndex(boot_td)
        hr = hit_fn(boot_signals, rates, h)
        br = base_fn(boot_idx, rates, h)
        if not br or np.isnan(br) or np.isnan(hr):
            continue
        boot_lifts.append(hr / br)

    if len(boot_lifts) < 50:
        return float("nan"), float("nan")

    alpha = 1 - confidence_level
    return (
        float(np.quantile(boot_lifts, alpha / 2)),       # two-sided lower bound
        float(np.quantile(boot_lifts, 1 - alpha / 2)),   # two-sided upper bound
    )


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
