"""OOT validation: run walk-forward backtest on all 5 corridors, report OOT lift.

Usage:
    python scripts/run_oot_validation.py

Output:
    - Table printed to stdout
    - reports/oot_validation_{date}.json
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from src.backtest.engine import run_walkforward
from src.indicators.log_return_percentile import LogReturnPercentileIndicator

CORRIDORS = ["RUB_KGS", "RUB_TJS", "RUB_UZS", "RUB_AMD", "RUB_KZT"]
DATA_PATH = "data/processed/rates.parquet"
H_REPORT = [1, 3, 5, 10, 20]
CI_HORIZONS = [5, 10, 20]


def main() -> None:
    df = pd.read_parquet(DATA_PATH)

    indicator = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.20, confirm_days=2
    )

    results = []
    for corridor in CORRIDORS:
        print(f"Running {corridor}...", flush=True)
        result = run_walkforward(
            indicator=indicator,
            corridor=corridor,
            df=df,
            train_years=2,
            test_months=3,
            h_horizons=H_REPORT,
            cooldown_days=3,
            embargo_days=5,
            save_report=True,
            compute_ci=True,
            ci_horizons=CI_HORIZONS,
            regime_filter=True,
        )
        results.append(result)

    # Print summary table
    print("\n" + "=" * 90)
    print(f"{'Corridor':<12} {'h':>3} {'IS Lift':>8} {'OOT Lift':>9} {'CI low':>7} {'CI hi':>7} {'N':>4} {'Freq/wk':>8}")
    print("-" * 90)
    for r in results:
        for h in H_REPORT:
            is_lift = r.lift.get(h, float("nan"))
            oot_lift = r.out_of_time_lift.get(h, float("nan"))
            ci_lo = r.lift_ci_low.get(h, float("nan"))
            ci_hi = r.lift_ci_high.get(h, float("nan"))

            def fmt(v: float) -> str:
                return f"{v:.3f}" if not (v != v) else "  NaN"

            print(
                f"{r.corridor:<12} {h:>3} {fmt(is_lift):>8} {fmt(oot_lift):>9} "
                f"{fmt(ci_lo):>7} {fmt(ci_hi):>7} {r.signal_count:>4} {r.signals_per_week:>8.3f}"
            )
        print()

    # Save JSON summary
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    stamp = date.today().isoformat()
    summary = [r.to_json() for r in results]
    out_path = out_dir / f"oot_validation_{stamp}.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nSaved → {out_path}")

    # Highlight corridors that pass CI lower > 1.0 at any horizon
    print("\n--- Corridors with CI lower > 1.0 ---")
    for r in results:
        for h in H_REPORT:
            ci_lo = r.lift_ci_low.get(h, float("nan"))
            if ci_lo == ci_lo and ci_lo > 1.0:
                oot = r.out_of_time_lift.get(h, float("nan"))
                print(f"  {r.corridor} h={h}: IS lift={r.lift[h]:.3f}, CI low={ci_lo:.3f}, OOT lift={oot:.3f}")


if __name__ == "__main__":
    main()
