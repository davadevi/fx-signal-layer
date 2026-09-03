"""CLI entrypoint: python -m src.pipeline.run --cutoff-date 2024-06-15"""
from __future__ import annotations

import argparse
from datetime import date

from src.pipeline.signals import generate_signals


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate FX signals for a given date")
    parser.add_argument("--cutoff-date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--corridors", nargs="+", help="Corridors to check (default: all 5)")
    parser.add_argument(
        "--cooldown", type=int, default=3, help="Cooldown days between signals"
    )
    parser.add_argument(
        "--require-rsi", action="store_true", help="Require RSI filter to confirm"
    )
    args = parser.parse_args()

    cutoff = date.fromisoformat(args.cutoff_date)
    signals = generate_signals(
        cutoff_date=cutoff,
        corridors=args.corridors,
        cooldown_days=args.cooldown,
        require_rsi=args.require_rsi,
    )

    if not signals:
        print(f"No signals on {cutoff}")
        return

    print(f"\nSignals for {cutoff}:\n")
    header = (
        f"{'Corridor':<12} {'Direction':<18} {'Strength':>8} "
        f"{'Pct':>6} {'Regime':>8}  Push Text"
    )
    print(header)
    print("-" * 100)
    for s in signals:
        print(
            f"{s.corridor:<12} {s.direction:<18} {s.strength:>8.3f} "
            f"{s.percentile_rank:>6.3f} {s.regime:>8}  {s.push_text}"
        )


if __name__ == "__main__":
    main()
