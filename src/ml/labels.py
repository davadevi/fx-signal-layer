"""Binary labels for ML training: rate[t+h] >= rate[t] (definition A hit).

Uses the full forward-filled daily rate series so that t+h is defined for
every trading day t. Labels are used ONLY for training rows; scoring never
touches the label series.
"""
from __future__ import annotations

import pandas as pd


def make_labels(
    df: pd.DataFrame,
    corridor: str,
    h: int = 5,
) -> pd.Series:
    """Binary label indexed by trading-day date.

    1 = hit (rate[t+h] >= rate[t], transferring at t was a good call)
    0 = miss (rate fell further)
    NaN = no t+h data available
    """
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

    sub = df[df["corridor"] == corridor].sort_values("date")
    if sub.empty:
        return pd.Series(dtype=float, name=f"label_h{h}")

    s = sub.set_index("date")["rate"]
    full_idx = pd.date_range(sub["date"].min(), sub["date"].max(), freq="D")
    rates_full = s.reindex(full_idx).ffill()

    trading_days = pd.DatetimeIndex(
        sub.loc[sub["is_trading_day"], "date"].sort_values().drop_duplicates().values
    )

    max_date = rates_full.index.max()
    labels: dict[pd.Timestamp, float] = {}
    for t in trading_days:
        t_plus = t + pd.Timedelta(days=h)
        if t not in rates_full.index or t_plus > max_date:
            labels[t] = float("nan")
            continue
        r_t = rates_full.loc[t]
        r_h = rates_full.loc[t_plus]
        if pd.isna(r_t) or pd.isna(r_h):
            labels[t] = float("nan")
            continue
        labels[t] = 1.0 if r_h >= r_t else 0.0

    return pd.Series(labels, name=f"label_h{h}")
