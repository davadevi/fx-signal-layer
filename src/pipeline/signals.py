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
    # Secondary: absolute-level percentile — kept for reporting only.
    primary_ind = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.20, confirm_days=2
    )
    pct_ind = PercentileRankIndicator()
    rsi_ind = RSIFilter()
    regime_ind = VolatilityRegimeFilter()

    candidates: list[Signal] = []
    for corridor in corridor_list:
        primary_scores = primary_ind.compute(df, corridor, cutoff_date)
        pct_scores = pct_ind.compute(df, corridor, cutoff_date)
        regime_scores = regime_ind.compute(df, corridor, cutoff_date)
        rsi_scores = rsi_ind.compute(df, corridor, cutoff_date)

        if key not in primary_scores.index or pd.isna(primary_scores.loc[key]):
            continue
        primary_val = float(primary_scores.loc[key])
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
        if primary_val >= primary_ind.threshold:
            continue
        if require_rsi and (rsi_val is None or rsi_val > rsi_ind.threshold / 100.0):
            continue

        rate = _current_rate(df, corridor, cutoff_date)
        if rate is None:
            continue

        push = format_push_text(corridor, primary_val, rate, "favorable_now")
        candidates.append(
            Signal(
                date=cutoff_date,
                corridor=corridor,
                indicator=primary_ind.name,
                direction="favorable_now",
                strength=1.0 - primary_val,
                push_text=push,
                percentile_rank=pct_val,
                rsi_score=rsi_val,
                regime=regime_str,
            )
        )

    candidates.sort(key=lambda s: s.strength, reverse=True)
    return candidates[:max_per_week]
