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

# Only confirm_days=2 (strong) variant is used. Validated: KGS lift 1.60, TJS 1.48,
# CI lower > 1.07. The weak (confirm=0) combo is excluded — its CI does not pass 1.0.

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
    cooldown_days: int = 3,
    max_signals: int = 2,
    require_rsi: bool = False,
    signal_history: list[date] | None = None,
) -> list[Signal]:
    """Generate favorable-rate signals for a single cutoff_date.

    Only data with date <= cutoff_date is used. Signals in a crisis volatility
    regime are suppressed. Result is capped at max_signals per call.

    signal_history: previous signal dates for cross-call cooldown. Caller must
        persist and pass this on each invocation.
    """
    if df is None:
        df = pd.read_parquet(DATA_PATH)
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

    corridor_list = corridors or MAIN_CORRIDORS
    key = pd.Timestamp(cutoff_date)

    signal_ind = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.20, confirm_days=2
    )
    pct_ind = PercentileRankIndicator()
    rsi_ind = RSIFilter()
    regime_ind = VolatilityRegimeFilter()

    candidates: list[Signal] = []
    for corridor in corridor_list:
        scores = signal_ind.compute(df, corridor, cutoff_date)
        pct_scores = pct_ind.compute(df, corridor, cutoff_date)
        regime_scores = regime_ind.compute(df, corridor, cutoff_date)
        rsi_scores = rsi_ind.compute(df, corridor, cutoff_date)

        score_val = (
            float(scores.loc[key])
            if key in scores.index and not pd.isna(scores.loc[key])
            else float("nan")
        )

        if pd.isna(score_val) or score_val >= signal_ind.threshold:
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

        push = format_push_text(corridor, score_val, rate, "favorable_now")
        candidates.append(
            Signal(
                date=cutoff_date,
                corridor=corridor,
                indicator="log_return_percentile",
                direction="favorable_now",
                strength=1.0 - score_val,
                push_text=push,
                percentile_rank=pct_val,
                rsi_score=rsi_val,
                regime=regime_str,
                tier="mandatory",
            )
        )

    history: list[date] = list(signal_history) if signal_history else []

    kept: list[Signal] = []
    candidates.sort(key=lambda s: s.strength, reverse=True)
    for s in candidates:
        if any(abs((s.date - h).days) < cooldown_days for h in history):
            continue
        kept.append(s)
        history.append(s.date)
        if len(kept) >= max_signals:
            break

    return kept
