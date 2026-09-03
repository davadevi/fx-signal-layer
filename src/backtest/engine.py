"""Walk-forward backtest engine (purged, embargoed).

Rolling train window (train_years), test window (test_months), quarterly step.
Embargo gap between train end and test start. Indicator sees only data with
date <= test window end. Signals are the trading days within the test window
where the score crosses the indicator's threshold in the favorable direction.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from dateutil.relativedelta import relativedelta

from src.backtest.metrics import (
    apply_cooldown,
    base_rate_at_h,
    base_rate_at_h_below_avg,
    clustering_score,
    cost_of_waiting_bps,
    hit_rate_at_h,
    hit_rate_at_h_below_avg,
    lift_confidence_interval,
    lift_over_random,
    lift_over_random_b,
)
from src.indicators.base import BaseIndicator

TRAIN_START = date(2022, 4, 1)
H_HORIZONS = [1, 3, 5, 10, 20]
OOT_START = date(2024, 1, 1)


@dataclass
class BacktestResult:
    indicator: str
    corridor: str
    hit_rate: dict[int, float]           # definition A: rate[t+h] >= rate[t]
    lift: dict[int, float]               # definition A lift
    hit_rate_b: dict[int, float]         # definition B: rate[t] < mean future
    lift_b: dict[int, float]             # definition B lift
    lift_ci_low: dict[int, float]        # 95% CI lower (definition A)
    lift_ci_high: dict[int, float]       # 95% CI upper (definition A)
    out_of_time_lift: dict[int, float]
    out_of_time_lift_b: dict[int, float]
    signal_count: int
    signals_per_week: float
    clustering_score: float
    cost_of_waiting_bps: float
    n_test_windows: int
    base_rate: dict[int, float]
    base_rate_b: dict[int, float]

    def to_json(self) -> dict:
        def _d(x: dict[int, float]) -> dict[str, float]:
            return {str(k): v for k, v in x.items()}

        return {
            "indicator": self.indicator,
            "corridor": self.corridor,
            "hit_rate": _d(self.hit_rate),
            "lift": _d(self.lift),
            "hit_rate_b": _d(self.hit_rate_b),
            "lift_b": _d(self.lift_b),
            "lift_ci_low": _d(self.lift_ci_low),
            "lift_ci_high": _d(self.lift_ci_high),
            "out_of_time_lift": _d(self.out_of_time_lift),
            "out_of_time_lift_b": _d(self.out_of_time_lift_b),
            "signal_count": self.signal_count,
            "signals_per_week": self.signals_per_week,
            "clustering_score": self.clustering_score,
            "cost_of_waiting_bps": self.cost_of_waiting_bps,
            "n_test_windows": self.n_test_windows,
            "base_rate": _d(self.base_rate),
            "base_rate_b": _d(self.base_rate_b),
        }


def _signal_direction(indicator: BaseIndicator) -> str:
    """Which side of threshold fires the signal.

    Percentile/momentum/RSI: signal when score BELOW threshold ("below").
    Volatility regime is a filter (get_signal not used directly by engine).
    Default: "below" for the indicators we ship.
    """
    name = getattr(indicator, "name", "")
    if name in {"percentile_rank", "rsi_filter", "momentum", "log_return_percentile", "log_ret_combined", "bollinger_zscore", "calendar_seasonality", "log_ret_and_calendar"}:
        return "below"
    return "above"


def _build_full_rate_series(df: pd.DataFrame, corridor: str) -> pd.Series:
    """Full daily index, forward-filled — needed for t+h lookups on weekends."""
    sub = df[df["corridor"] == corridor].sort_values("date")
    if sub.empty:
        return pd.Series(dtype=float)
    s = sub.set_index("date")["rate"]
    full_idx = pd.date_range(sub["date"].min(), sub["date"].max(), freq="D")
    return s.reindex(full_idx).ffill()


def run_walkforward(
    indicator: BaseIndicator,
    corridor: str,
    df: pd.DataFrame,
    train_years: int = 2,
    test_months: int = 3,
    h_horizons: list[int] | None = None,
    cooldown_days: int = 3,
    embargo_days: int = 5,
    save_report: bool = True,
    reports_dir: str = "reports",
    compute_ci: bool = True,
    ci_horizons: list[int] | None = None,
) -> BacktestResult:
    horizons = list(h_horizons) if h_horizons else list(H_HORIZONS)

    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

    rates_full = _build_full_rate_series(df, corridor)
    if rates_full.empty:
        raise ValueError(f"No data for corridor {corridor}")

    corridor_df = df[df["corridor"] == corridor].copy()
    max_h = max(horizons)
    data_end = corridor_df["date"].max().date()
    last_test_end = data_end - timedelta(days=max_h)

    direction = _signal_direction(indicator)
    threshold = getattr(indicator, "threshold", 0.5)
    if indicator.name == "rsi_filter":
        threshold = threshold / 100.0  # RSI stored as 0-100, score in [0,1]

    # Generate quarterly test windows
    all_signals: list[date] = []
    all_trading_days: list[pd.Timestamp] = []
    oot_signals: list[date] = []
    oot_trading_days: list[pd.Timestamp] = []
    n_windows = 0

    test_start = TRAIN_START + relativedelta(years=train_years)
    while test_start <= last_test_end:
        test_end = min(
            test_start + relativedelta(months=test_months) - timedelta(days=1),
            last_test_end,
        )
        # Compute scores once with cutoff = test_end
        scores = indicator.compute(df, corridor, test_end)

        # Embargo: skip first embargo_days of test window to prevent label overlap
        # between the indicator's rolling lookback and test signal extraction.
        effective_test_start = test_start + timedelta(days=embargo_days)
        window_mask = (corridor_df["date"] >= pd.Timestamp(effective_test_start)) & (
            corridor_df["date"] <= pd.Timestamp(test_end)
        )
        window_days = corridor_df.loc[window_mask & corridor_df["is_trading_day"], "date"]
        # Threshold scores → signal days (raw, before cooldown)
        raw_signals: list[date] = []
        for ts in window_days:
            if ts not in scores.index or pd.isna(scores.loc[ts]):
                continue
            score = scores.loc[ts]
            fires = score < threshold if direction == "below" else score >= threshold
            if fires:
                raw_signals.append(ts.date())
        cd_signals = apply_cooldown(raw_signals, cooldown_days=cooldown_days)

        all_signals.extend(cd_signals)
        all_trading_days.extend(list(window_days))
        if test_start >= OOT_START:
            oot_signals.extend(cd_signals)
            oot_trading_days.extend(list(window_days))

        n_windows += 1
        test_start = test_start + relativedelta(months=test_months)

    trading_idx = pd.DatetimeIndex(all_trading_days)
    oot_idx = pd.DatetimeIndex(oot_trading_days)

    hit_rate = {h: hit_rate_at_h(all_signals, rates_full, h) for h in horizons}
    base_rate = {h: base_rate_at_h(trading_idx, rates_full, h) for h in horizons}
    lift = {h: lift_over_random(all_signals, rates_full, trading_idx, h) for h in horizons}
    oot_lift = {h: lift_over_random(oot_signals, rates_full, oot_idx, h) for h in horizons}

    hit_rate_b = {h: hit_rate_at_h_below_avg(all_signals, rates_full, h) for h in horizons}
    base_rate_b = {h: base_rate_at_h_below_avg(trading_idx, rates_full, h) for h in horizons}
    lift_b = {h: lift_over_random_b(all_signals, rates_full, trading_idx, h) for h in horizons}
    oot_lift_b = {h: lift_over_random_b(oot_signals, rates_full, oot_idx, h) for h in horizons}

    ci_hs = ci_horizons if ci_horizons is not None else [5]
    lift_ci_low: dict[int, float] = {}
    lift_ci_high: dict[int, float] = {}
    if compute_ci and all_signals:
        for h in horizons:
            if h in ci_hs:
                lo, hi = lift_confidence_interval(
                    all_signals, rates_full, trading_idx, h, definition="A"
                )
                lift_ci_low[h] = lo
                lift_ci_high[h] = hi
            else:
                lift_ci_low[h] = float("nan")
                lift_ci_high[h] = float("nan")
    else:
        lift_ci_low = {h: float("nan") for h in horizons}
        lift_ci_high = {h: float("nan") for h in horizons}

    # signals per week: over the total test period
    if all_trading_days:
        span_days = (max(all_trading_days) - min(all_trading_days)).days + 1
        weeks = max(span_days / 7.0, 1e-9)
        signals_per_week = len(all_signals) / weeks
    else:
        signals_per_week = 0.0

    result = BacktestResult(
        indicator=indicator.name,
        corridor=corridor,
        hit_rate=hit_rate,
        lift=lift,
        hit_rate_b=hit_rate_b,
        lift_b=lift_b,
        lift_ci_low=lift_ci_low,
        lift_ci_high=lift_ci_high,
        out_of_time_lift=oot_lift,
        out_of_time_lift_b=oot_lift_b,
        signal_count=len(all_signals),
        signals_per_week=signals_per_week,
        clustering_score=clustering_score(all_signals),
        cost_of_waiting_bps=cost_of_waiting_bps(all_signals, rates_full),
        n_test_windows=n_windows,
        base_rate=base_rate,
        base_rate_b=base_rate_b,
    )

    if save_report:
        out_dir = Path(reports_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = date.today().isoformat()
        out_path = out_dir / f"{indicator.name}_{corridor}_{stamp}.json"
        out_path.write_text(json.dumps(result.to_json(), indent=2, ensure_ascii=False))

    return result
