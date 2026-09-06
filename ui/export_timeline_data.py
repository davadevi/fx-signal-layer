"""Export a compact browser dataset for the historical notification demo."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TypedDict, cast

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT_ROOT / "data" / "processed" / "rates.parquet"
TARGET = Path(__file__).resolve().parent / "timeline-data.json"
START_DATE = "2022-04-01"
SUPPORTED = {"AMD", "KGS", "KZT", "TJS", "UZS"}
REQUIRED_COLUMNS = {"date", "corridor", "rate", "is_trading_day"}
CORRIDOR_TO_CURRENCY = {
    "RUB_AMD": "AMD",
    "RUB_KGS": "KGS",
    "RUB_KZT": "KZT",
    "RUB_TJS": "TJS",
    "RUB_UZS": "UZS",
}


class TimelinePayload(TypedDict):
    """JSON-compatible data consumed by ``timeline-demo.js``."""

    source: str
    generated_from: str
    start_date: str
    end_date: str
    series: dict[str, list[list[str | float]]]


def build_payload(source: Path = SOURCE) -> TimelinePayload:
    """Build the browser payload from the repository's normalized rate data."""
    if not source.is_file():
        raise FileNotFoundError(
            f"Rate data not found at {source}. Run `python -m src.data.download` first."
        )

    frame = pd.read_parquet(source)
    missing_columns = REQUIRED_COLUMNS.difference(frame.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Rate data is missing required columns: {missing}")

    frame = frame.loc[:, sorted(REQUIRED_COLUMNS)].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame["rate"] = pd.to_numeric(frame["rate"], errors="raise")
    frame = frame.loc[
        frame["corridor"].isin(CORRIDOR_TO_CURRENCY)
        & frame["is_trading_day"].eq(True)
        & frame["date"].ge(START_DATE)
    ].copy()

    if frame.empty:
        raise ValueError(f"Rate data has no supported observations on or after {START_DATE}")

    duplicate_rows = frame.duplicated(subset=["corridor", "date"], keep=False)
    if duplicate_rows.any():
        raise ValueError("Rate data contains duplicate corridor/date observations")

    if not frame["rate"].map(math.isfinite).all():
        raise ValueError("Rate data contains a non-finite rate")

    currencies = {CORRIDOR_TO_CURRENCY[corridor] for corridor in frame["corridor"]}
    missing_currencies = SUPPORTED.difference(currencies)
    if missing_currencies:
        missing = ", ".join(sorted(missing_currencies))
        raise ValueError(f"Rate data has no observations for: {missing}")

    frame["date_string"] = frame["date"].dt.strftime("%Y-%m-%d")
    series: dict[str, list[list[str | float]]] = {currency: [] for currency in sorted(SUPPORTED)}
    for row in frame.sort_values(["corridor", "date"]).itertuples(index=False):
        corridor = cast(str, row.corridor)
        date_string = cast(str, row.date_string)
        rate = cast(float, row.rate)
        currency = CORRIDOR_TO_CURRENCY[corridor]
        series[currency].append([date_string, round(float(rate), 8)])

    return {
        "source": "CBR daily official rates; rub_per_unit",
        "generated_from": str(source.relative_to(PROJECT_ROOT)),
        "start_date": str(frame["date_string"].min()),
        "end_date": str(frame["date_string"].max()),
        "series": series,
    }


def main() -> None:
    payload = build_payload()
    TARGET.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {TARGET} with {sum(map(len, payload['series'].values()))} observations")


if __name__ == "__main__":
    main()
