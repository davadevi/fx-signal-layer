"""Feature matrix built from indicator scores.

All features respect the cutoff_date lookahead boundary: each indicator's
compute() is called with the same cutoff, and the resulting scores are aligned
on the trading-day index of the corridor up to (and including) cutoff_date.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.indicators.bollinger_zscore import BollingerZScoreIndicator
from src.indicators.calendar_seasonality import CalendarSeasonalityIndicator
from src.indicators.log_return_percentile import LogReturnPercentileIndicator
from src.indicators.percentile import PercentileRankIndicator
from src.indicators.rsi import RSIFilter
from src.indicators.volatility_regime import VolatilityRegimeFilter


FEATURE_COLUMNS: list[str] = [
    "log_ret_c0",
    "log_ret_c2",
    "pct_rank",
    "rsi",
    "regime",
    "bollinger_z",
    "calendar",
    "log_ret_c0_lag1",
    "log_ret_c0_lag2",
    "pct_rank_lag1",
]


def build_features(
    df: pd.DataFrame,
    corridor: str,
    cutoff_date: date,
) -> pd.DataFrame:
    """Build feature matrix for all trading days up to cutoff_date.

    Returns DataFrame indexed by DatetimeIndex (trading days only) with the
    columns listed in FEATURE_COLUMNS.
    """
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

    cutoff_ts = pd.Timestamp(cutoff_date)
    corridor_df = df[(df["corridor"] == corridor) & (df["date"] <= cutoff_ts)]
    trading_days = (
        corridor_df.loc[corridor_df["is_trading_day"], "date"]
        .sort_values()
        .drop_duplicates()
    )
    trading_idx = pd.DatetimeIndex(trading_days.values)

    if trading_idx.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    log_ret_c0_ind = LogReturnPercentileIndicator(confirm_days=0)
    log_ret_c2_ind = LogReturnPercentileIndicator(confirm_days=2)
    pct_rank_ind = PercentileRankIndicator()
    rsi_ind = RSIFilter()
    regime_ind = VolatilityRegimeFilter()
    boll_ind = BollingerZScoreIndicator()
    cal_ind = CalendarSeasonalityIndicator()

    scores = {
        "log_ret_c0": log_ret_c0_ind.compute(df, corridor, cutoff_date),
        "log_ret_c2": log_ret_c2_ind.compute(df, corridor, cutoff_date),
        "pct_rank": pct_rank_ind.compute(df, corridor, cutoff_date),
        "rsi": rsi_ind.compute(df, corridor, cutoff_date),
        "regime": regime_ind.compute(df, corridor, cutoff_date),
        "bollinger_z": boll_ind.compute(df, corridor, cutoff_date),
        "calendar": cal_ind.compute(df, corridor, cutoff_date),
    }

    out = pd.DataFrame(index=trading_idx)
    for name, s in scores.items():
        out[name] = s.reindex(trading_idx)

    # Lags: computed over the trading-day index (not calendar days) so that
    # "lag1" = previous trading day, unaffected by weekend forward-fills.
    out["log_ret_c0_lag1"] = out["log_ret_c0"].shift(1)
    out["log_ret_c0_lag2"] = out["log_ret_c0"].shift(2)
    out["pct_rank_lag1"] = out["pct_rank"].shift(1)

    return out[FEATURE_COLUMNS]
