"""Signal pipeline: combines indicators into a per-corridor signal list."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from src.indicators import (
    LogReturnPercentileIndicator,
    PercentileRankIndicator,
    RSIFilter,
    VolatilityRegimeFilter,
)
from src.texts.templates import format_push_text

MAIN_CORRIDORS = ["RUB_TJS", "RUB_UZS", "RUB_KGS", "RUB_AMD", "RUB_KZT"]
DATA_PATH = "data/processed/rates.parquet"


@dataclass
class Signal:
    date: date
    corridor: str
    indicator: str
    direction: str
    strength: float
    push_text: str
    percentile_rank: float
    rsi_score: float | None
    regime: str
    tier: str  # "mandatory" | "optional"


def _current_rate(df: pd.DataFrame, corridor: str, cutoff_date: date) -> float | None:
    sub = df[(df["corridor"] == corridor) & (df["date"] <= pd.Timestamp(cutoff_date))]
    if sub.empty:
        return None
    return float(sub.sort_values("date")["rate"].iloc[-1])


def generate_signals(
    cutoff_date: date,
    df: pd.DataFrame | None = None,
    corridors: list[str] | None = None,
    cooldown_days: int = 3,  # noqa: ARG001 — reserved for full history-aware cooldown
    max_per_week: int = 2,
    require_rsi: bool = False,
) -> list[Signal]:
    """Generate favorable-rate signals for a single cutoff_date.

    Only data with date <= cutoff_date is used. Signals in a crisis volatility
    regime are suppressed. Result is capped at max_per_week per call.
    """
    if df is None:
        df = pd.read_parquet(DATA_PATH)
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

    corridor_list = corridors or MAIN_CORRIDORS
    key = pd.Timestamp(cutoff_date)

    # Primary signal: log-return percentile (I(0) transform, valid on trending series).
    # OR-combination: strong (confirm=2) OR weak (confirm=0). Strong has priority.
    # Secondary: absolute-level percentile — kept for reporting only.
    strong_ind = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.20, confirm_days=2
    )
    weak_ind = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.20, confirm_days=0
    )
    pct_ind = PercentileRankIndicator()
    rsi_ind = RSIFilter()
    regime_ind = VolatilityRegimeFilter()

    candidates: list[Signal] = []
    for corridor in corridor_list:
        strong_scores = strong_ind.compute(df, corridor, cutoff_date)
        weak_scores = weak_ind.compute(df, corridor, cutoff_date)
        pct_scores = pct_ind.compute(df, corridor, cutoff_date)
        regime_scores = regime_ind.compute(df, corridor, cutoff_date)
        rsi_scores = rsi_ind.compute(df, corridor, cutoff_date)

        strong_val = (
            float(strong_scores.loc[key])
            if key in strong_scores.index and not pd.isna(strong_scores.loc[key])
            else float("nan")
        )
        weak_val = (
            float(weak_scores.loc[key])
            if key in weak_scores.index and not pd.isna(weak_scores.loc[key])
            else float("nan")
        )

        strong_fires = not pd.isna(strong_val) and strong_val < strong_ind.threshold
        weak_fires = not pd.isna(weak_val) and weak_val < weak_ind.threshold
        if not (strong_fires or weak_fires):
            continue

        pct_val = (
            float(pct_scores.loc[key])
            if key in pct_scores.index and not pd.isna(pct_scores.loc[key])
            else float("nan")
        )
        regime_val = float(regime_scores.loc[key]) if key in regime_scores.index else 1.0
        regime_str = "calm" if regime_val >= 0.5 else "crisis"
        rsi_val = (
            float(rsi_scores.loc[key])
            if key in rsi_scores.index and not pd.isna(rsi_scores.loc[key])
            else None
        )

        if regime_str == "crisis":
            continue
        if require_rsi and (rsi_val is None or rsi_val > rsi_ind.threshold / 100.0):
            continue

        rate = _current_rate(df, corridor, cutoff_date)
        if rate is None:
            continue

        if strong_fires:
            indicator_name = "log_return_percentile_strong"
            strength = 1.0 - strong_val
            score_for_text = strong_val
            tier = "mandatory"
        else:
            indicator_name = "log_return_percentile_weak"
            strength = 0.5 * (1.0 - weak_val)
            score_for_text = weak_val
            tier = "optional"

        push = format_push_text(corridor, score_for_text, rate, "favorable_now")
        candidates.append(
            Signal(
                date=cutoff_date,
                corridor=corridor,
                indicator=indicator_name,
                direction="favorable_now",
                strength=strength,
                push_text=push,
                percentile_rank=pct_val,
                rsi_score=rsi_val,
                regime=regime_str,
                tier=tier,
            )
        )

    mandatory = [s for s in candidates if s.tier == "mandatory"]
    optional = [s for s in candidates if s.tier == "optional"]

    # Mandatory: all pass, no cooldown, no cap.
    # Optional: cooldown check against ALL signals (mandatory + already-kept optional),
    # then cap by remaining slots (max_per_week - len(mandatory), min 0).
    mandatory.sort(key=lambda s: s.strength, reverse=True)
    optional.sort(key=lambda s: s.strength, reverse=True)

    kept_optional: list[Signal] = []
    all_kept_dates: list[date] = [s.date for s in mandatory]
    for s in optional:
        conflict = any(
            abs((s.date - d).days) < cooldown_days for d in all_kept_dates
        )
        if conflict:
            continue
        kept_optional.append(s)
        all_kept_dates.append(s.date)

    remaining_slots = max(max_per_week - len(mandatory), 0)
    kept_optional = kept_optional[:remaining_slots]

    return mandatory + kept_optional
