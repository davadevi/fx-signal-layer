import importlib.util
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest


def _load_exporter() -> ModuleType:
    module_path = Path(__file__).resolve().parents[2] / "ui" / "export_timeline_data.py"
    spec = importlib.util.spec_from_file_location("export_timeline_data", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load timeline exporter from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exporter = _load_exporter()


def _source_file(tmp_path: Path) -> Path:
    source = tmp_path / "data" / "processed" / "rates.parquet"
    source.parent.mkdir(parents=True)
    source.touch()
    return source


def test_build_payload_uses_supported_trading_days(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _source_file(tmp_path)
    rows: list[dict[str, object]] = []
    for currency in reversed(sorted(exporter.SUPPORTED)):
        rows.extend(
            [
                {
                    "date": "2022-04-03",
                    "corridor": f"RUB_{currency}",
                    "rate": 1.123456789,
                    "is_trading_day": True,
                },
                {
                    "date": "2022-04-01",
                    "corridor": f"RUB_{currency}",
                    "rate": 2,
                    "is_trading_day": True,
                },
            ]
        )
    rows.extend(
        [
            {
                "date": "2022-04-02",
                "corridor": "RUB_AMD",
                "rate": 99,
                "is_trading_day": False,
            },
            {
                "date": "2022-03-31",
                "corridor": "RUB_KGS",
                "rate": 99,
                "is_trading_day": True,
            },
            {
                "date": "2022-04-02",
                "corridor": "RUB_USD",
                "rate": 99,
                "is_trading_day": True,
            },
        ]
    )
    frame = pd.DataFrame(rows)
    monkeypatch.setattr(exporter, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(exporter.pd, "read_parquet", lambda path: frame)

    payload = exporter.build_payload(source)

    assert payload["generated_from"] == "data/processed/rates.parquet"
    assert payload["start_date"] == "2022-04-01"
    assert payload["end_date"] == "2022-04-03"
    assert list(payload["series"]) == sorted(exporter.SUPPORTED)
    assert payload["series"]["AMD"] == [
        ["2022-04-01", 2.0],
        ["2022-04-03", 1.12345679],
    ]


def test_build_payload_rejects_duplicate_observations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _source_file(tmp_path)
    rows = [
        {
            "date": "2022-04-01",
            "corridor": f"RUB_{currency}",
            "rate": 1,
            "is_trading_day": True,
        }
        for currency in sorted(exporter.SUPPORTED)
    ]
    rows.append(rows[0].copy())
    monkeypatch.setattr(exporter, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(exporter.pd, "read_parquet", lambda path: pd.DataFrame(rows))

    with pytest.raises(ValueError, match="duplicate corridor/date"):
        exporter.build_payload(source)
