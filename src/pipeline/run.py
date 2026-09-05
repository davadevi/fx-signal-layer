"""CLI entrypoint: python -m src.pipeline.run --cutoff-date 2024-06-15"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from src.pipeline.signals import generate_signals

HISTORY_PATH = Path("data/signal_history.json")
HISTORY_RETENTION_DAYS = 30


def _load_history() -> list[date]:
    if not HISTORY_PATH.exists():
        return []
    try:
        raw = json.loads(HISTORY_PATH.read_text())
        cutoff = date.today() - timedelta(days=HISTORY_RETENTION_DAYS)
        return [date.fromisoformat(r["date"]) for r in raw if date.fromisoformat(r["date"]) >= cutoff]
    except Exception:
        return []


def _save_history(existing: list[date], new_signals: list) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    cutoff = date.today() - timedelta(days=HISTORY_RETENTION_DAYS)
    records = [{"date": d.isoformat()} for d in existing if d >= cutoff]
    for s in new_signals:
        records.append({"date": s.date.isoformat(), "corridor": s.corridor})
    HISTORY_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False))


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
    history = _load_history()

    signals = generate_signals(
        cutoff_date=cutoff,
        corridors=args.corridors,
        cooldown_days=args.cooldown,
        require_rsi=args.require_rsi,
        signal_history=history,
    )

    _save_history(history, signals)

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
