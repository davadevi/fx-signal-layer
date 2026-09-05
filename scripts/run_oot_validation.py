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


def _fmt(v: float) -> str:
    return f"{v:.3f}" if v == v else "  NaN"


def _fmt_bps(v: float) -> str:
    if v != v:
        return "   NaN"
    return f"{v:+.1f}"


def run_indicator(indicator: "LogReturnPercentileIndicator", df: pd.DataFrame) -> list:
    results = []
    for corridor in CORRIDORS:
        print(f"  {corridor}...", flush=True)
        result = run_walkforward(
            indicator=indicator,
            corridor=corridor,
            df=df,
            train_years=2,
            test_months=3,
            h_horizons=H_REPORT,
            cooldown_days=3,
            embargo_days=5,
            save_report=False,
            compute_ci=True,
            ci_horizons=CI_HORIZONS,
            regime_filter=True,
        )
        results.append(result)
    return results


def print_table(results: list, title: str) -> None:
    print(f"\n{title}")
    print("=" * 105)
    print(f"{'Corridor':<12} {'h':>3} {'IS Lift':>8} {'OOT Lift':>9} {'CI low':>7} {'CI hi':>7} "
          f"{'bps@h':>7} {'N':>4} {'Freq/wk':>8}")
    print("-" * 105)
    for r in results:
        for h in H_REPORT:
            is_lift = r.lift.get(h, float("nan"))
            oot_lift = r.out_of_time_lift.get(h, float("nan"))
            ci_lo = r.lift_ci_low.get(h, float("nan"))
            ci_hi = r.lift_ci_high.get(h, float("nan"))
            bps_h = r.bps_by_horizon.get(h, float("nan"))
            print(
                f"{r.corridor:<12} {h:>3} {_fmt(is_lift):>8} {_fmt(oot_lift):>9} "
                f"{_fmt(ci_lo):>7} {_fmt(ci_hi):>7} {_fmt_bps(bps_h):>7} "
                f"{r.signal_count:>4} {r.signals_per_week:>8.3f}"
            )
        print()


def main() -> None:
    df = pd.read_parquet(DATA_PATH)

    # ── c2: строгий вариант (confirm_days=2) ─────────────────────────────────
    print("Running c2 (confirm_days=2)...")
    ind_c2 = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.20, confirm_days=2
    )
    results_c2 = run_indicator(ind_c2, df)
    print_table(results_c2, "c2 (строгий, confirm_days=2) — основной вариант")

    # ── c0: частый вариант (confirm_days=0) ──────────────────────────────────
    print("\nRunning c0 (confirm_days=0)...")
    ind_c0 = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.20, confirm_days=0
    )
    results_c0 = run_indicator(ind_c0, df)
    print_table(results_c0, "c0 (частый, confirm_days=0) — сравнение по частоте")

    # ── c1: confirm_days=1 ────────────────────────────────────────────────────
    print("\nRunning c1 (confirm_days=1)...")
    ind_c1 = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.20, confirm_days=1
    )
    results_c1 = run_indicator(ind_c1, df)
    print_table(results_c1, "c1 (confirm_days=1) — мягче c2")

    # ── t25: threshold=0.25 ───────────────────────────────────────────────────
    print("\nRunning t25 (threshold=0.25, confirm_days=2)...")
    ind_t25 = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.25, confirm_days=2
    )
    results_t25 = run_indicator(ind_t25, df)
    print_table(results_t25, "t25 (threshold=0.25, confirm=2) — шире порог")

    # ── t30: threshold=0.30 ───────────────────────────────────────────────────
    print("\nRunning t30 (threshold=0.30, confirm_days=2)...")
    ind_t30 = LogReturnPercentileIndicator(
        return_window=5, rank_window=60, threshold=0.30, confirm_days=2
    )
    results_t30 = run_indicator(ind_t30, df)
    print_table(results_t30, "t30 (threshold=0.30, confirm=2) — ещё шире")

    # ── w30: rank_window=30 ───────────────────────────────────────────────────
    print("\nRunning w30 (rank_window=30, confirm_days=2)...")
    ind_w30 = LogReturnPercentileIndicator(
        return_window=5, rank_window=30, threshold=0.20, confirm_days=2
    )
    results_w30 = run_indicator(ind_w30, df)
    print_table(results_w30, "w30 (rank_window=30, confirm=2) — короткое окно")

    # ── Сохранить JSON ────────────────────────────────────────────────────────
    out_dir = Path("reports/validation")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    summary = {
        "c2": [r.to_json() for r in results_c2],
        "c0": [r.to_json() for r in results_c0],
        "c1": [r.to_json() for r in results_c1],
        "t25": [r.to_json() for r in results_t25],
        "t30": [r.to_json() for r in results_t30],
        "w30": [r.to_json() for r in results_w30],
    }
    out_path = out_dir / f"oot_validation_{stamp}.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nSaved → {out_path}")

    # ── Highlight c2: CI lower > 1.0 ─────────────────────────────────────────
    print("\n--- c2: Corridors with CI lower > 1.0 ---")
    for r in results_c2:
        for h in H_REPORT:
            ci_lo = r.lift_ci_low.get(h, float("nan"))
            if ci_lo == ci_lo and ci_lo > 1.0:
                oot = r.out_of_time_lift.get(h, float("nan"))
                bps_h = r.bps_by_horizon.get(h, float("nan"))
                print(
                    f"  {r.corridor} h={h}: IS={r.lift[h]:.3f}, CI↓={ci_lo:.3f}, "
                    f"OOT={_fmt(oot)}, bps={_fmt_bps(bps_h)}"
                )

    # ── Сводная таблица: все варианты ────────────────────────────────────────
    print("\n--- Сводная таблица: Freq/wk vs OOT CI↓ (h=5, h=10) ---")
    all_variants = {
        "c2": results_c2,
        "c0": results_c0,
        "c1": results_c1,
        "t25": results_t25,
        "t30": results_t30,
        "w30": results_w30,
    }
    print(f"{'Вариант':<8} {'Corridor':<12} {'Freq/wk':>8} {'CI↓ h=5':>9} "
          f"{'CI↓ h=10':>10} {'OOT h=5':>9} {'OOT h=10':>10} {'bps h=10':>9}")
    print("-" * 85)
    for name, res_list in all_variants.items():
        for r in res_list:
            ci5  = r.lift_ci_low.get(5, float("nan"))
            ci10 = r.lift_ci_low.get(10, float("nan"))
            ot5  = r.out_of_time_lift.get(5, float("nan"))
            ot10 = r.out_of_time_lift.get(10, float("nan"))
            bps10 = r.bps_by_horizon.get(10, float("nan"))
            print(
                f"{name:<8} {r.corridor:<12} {r.signals_per_week:>8.3f} "
                f"{_fmt(ci5):>9} {_fmt(ci10):>10} {_fmt(ot5):>9} {_fmt(ot10):>10} "
                f"{_fmt_bps(bps10):>9}"
            )


if __name__ == "__main__":
    main()
