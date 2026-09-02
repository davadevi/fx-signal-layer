"""CBR historical FX rate downloader.

Fetches daily official rates for the target corridors from the Central Bank of
Russia dynamic XML endpoint, forward-fills weekends/holidays and persists the
result as a parquet file.

No-lookahead rule: `download_rates` accepts a `cutoff_date`; when provided the
returned frame is filtered to rows with `date <= cutoff_date` before returning.
"""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

CBR_URL = "https://www.cbr.ru/scripts/XML_dynamic.asp"
CBR_ENCODING = "windows-1251"
REQUEST_TIMEOUT_S = 30
THROTTLE_S = 0.5

CURRENCIES: dict[str, str] = {
    "TJS": "R01670",  # Tajik somoni
    "UZS": "R01717",  # Uzbek sum
    "KGS": "R01370",  # Kyrgyz som
    "AMD": "R01060",  # Armenian dram
    "KZT": "R01335",  # Kazakh tenge
    "USD": "R01235",  # US dollar (context)
    "EUR": "R01239",  # Euro (context)
    "CNY": "R01375",  # Chinese yuan (context)
}


def _fetch_currency(
    val_nm_rq: str, start: date, end: date
) -> list[tuple[date, float]]:
    """Fetch (date, VunitRate) pairs for a single currency ID from CBR."""
    params = {
        "date_req1": start.strftime("%d/%m/%Y"),
        "date_req2": end.strftime("%d/%m/%Y"),
        "VAL_NM_RQ": val_nm_rq,
    }
    resp = requests.get(CBR_URL, params=params, timeout=REQUEST_TIMEOUT_S)
    resp.raise_for_status()
    xml_text = resp.content.decode(CBR_ENCODING)
    root = ET.fromstring(xml_text)

    rows: list[tuple[date, float]] = []
    for record in root.findall("Record"):
        date_str = record.attrib.get("Date")
        vunit_el = record.find("VunitRate")
        if date_str is None or vunit_el is None or vunit_el.text is None:
            continue
        d = datetime.strptime(date_str, "%d.%m.%Y").date()
        rate = float(vunit_el.text.replace(",", "."))
        rows.append((d, rate))
    return rows


def _forward_fill_corridor(
    rows: list[tuple[date, float]], start: date, end: date, corridor: str
) -> pd.DataFrame:
    """Build a continuous daily frame with forward-filled non-trading days."""
    if not rows:
        raise ValueError(f"No data returned for corridor {corridor}")

    published = pd.DataFrame(rows, columns=["date", "rate"])
    published["date"] = pd.to_datetime(published["date"])
    published = published.drop_duplicates(subset="date").sort_values("date")
    published["is_trading_day"] = True

    full_index = pd.date_range(start=start, end=end, freq="D")
    frame = (
        published.set_index("date")
        .reindex(full_index)
        .rename_axis("date")
        .reset_index()
    )
    frame["rate"] = frame["rate"].ffill()
    frame["is_trading_day"] = frame["is_trading_day"].fillna(False).astype(bool)
    # Drop leading rows before the first observed rate (nothing to ffill from).
    frame = frame.dropna(subset=["rate"]).reset_index(drop=True)
    frame["corridor"] = corridor
    return frame[["date", "corridor", "rate", "is_trading_day"]]


def download_rates(
    start: str = "2020-01-01", cutoff_date: date | None = None
) -> pd.DataFrame:
    """Download historical CBR rates for all configured currencies.

    Args:
        start: ISO date string for the first date to request.
        cutoff_date: If provided, resulting frame is filtered to
            `date <= cutoff_date` (no-lookahead safeguard).

    Returns:
        DataFrame with columns [date, corridor, rate, is_trading_day].
    """
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = date.today()

    per_corridor: list[pd.DataFrame] = []
    for iso, val_nm_rq in CURRENCIES.items():
        corridor = f"RUB_{iso}"
        rows = _fetch_currency(val_nm_rq, start_date, end_date)
        per_corridor.append(
            _forward_fill_corridor(rows, start_date, end_date, corridor)
        )
        time.sleep(THROTTLE_S)

    df = pd.concat(per_corridor, ignore_index=True)
    df = df.sort_values(["corridor", "date"]).reset_index(drop=True)

    if cutoff_date is not None:
        cutoff_ts = pd.Timestamp(cutoff_date)
        df = df[df["date"] <= cutoff_ts].reset_index(drop=True)

    return df


def save_rates(
    df: pd.DataFrame, path: str = "data/processed/rates.parquet"
) -> None:
    """Persist rates dataframe to parquet, creating parent dirs as needed."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)


if __name__ == "__main__":
    df = download_rates()
    save_rates(df)

    print(f"Saved {len(df)} rows to data/processed/rates.parquet")
    print(f"Shape: {df.shape}")
    print(f"Date range: {df['date'].min().date()} -> {df['date'].max().date()}")
    print(f"Corridors: {sorted(df['corridor'].unique().tolist())}")
    print("\nSample rows (one per corridor, latest date):")
    latest = (
        df.sort_values("date")
        .groupby("corridor", as_index=False)
        .tail(1)
        .sort_values("corridor")
    )
    print(latest.to_string(index=False))
