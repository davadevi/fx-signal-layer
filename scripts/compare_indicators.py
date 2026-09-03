"""Compare PercentileRankIndicator vs LogReturnPercentileIndicator across corridors.

Run: .venv/bin/python scripts/compare_indicators.py
"""
from __future__ import annotations

import pandas as pd

from src.backtest.engine import run_walkforward
from src.indicators import LogReturnPercentileIndicator, PercentileRankIndicator


CORRIDORS = ["RUB_TJS", "RUB_UZS", "RUB_KGS", "RUB_AMD", "RUB_KZT"]


def main() -> None:
    df = pd.read_parquet("data/processed/rates.parquet")
    df["date"] = pd.to_datetime(df["date"])

    indicators = [
        ("percentile_30d", PercentileRankIndicator(window=30, threshold=0.20)),
        (
            "log_ret_5d_60w",
            LogReturnPercentileIndicator(
                return_window=5, rank_window=60, threshold=0.20, confirm_days=0
            ),
        ),
        (
            "log_ret_5d_60w_confirm2",
            LogReturnPercentileIndicator(
                return_window=5, rank_window=60, threshold=0.20, confirm_days=2
            ),
        ),
    ]

    header = (
        f"{'Indicator':<28} {'Corridor':<10} "
        f"{'lift_A@5':>10} {'lift_B@5':>10} "
        f"{'CI_low@5':>10} {'CI_high@5':>10} "
        f"{'n_sig':>6} {'sig/wk':>7}"
    )
    print(header)
    print("-" * len(header))

    for ind_name, indicator in indicators:
        for corridor in CORRIDORS:
            r = run_walkforward(
                indicator, corridor, df, compute_ci=True, save_report=False
            )
            print(
                f"{ind_name:<28} {corridor:<10}"
                f" {r.lift.get(5, float('nan')):>10.3f}"
                f" {r.lift_b.get(5, float('nan')):>10.3f}"
                f" {r.lift_ci_low.get(5, float('nan')):>10.3f}"
                f" {r.lift_ci_high.get(5, float('nan')):>10.3f}"
                f" {r.signal_count:>6d}"
                f" {r.signals_per_week:>7.2f}"
            )


if __name__ == "__main__":
    main()
