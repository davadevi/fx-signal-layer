# Module Interfaces

## src/data

Реализовано: `src/data/download.py`

```python
def download_rates(
    start: str = "2020-01-01",
    cutoff_date: date | None = None,
) -> pd.DataFrame:
    """
    Скачивает курсы ЦБ РФ для всех 8 коридоров (TJS/UZS/KGS/AMD/KZT + USD/EUR/CNY).
    Возвращает DataFrame: [date, corridor, rate, is_trading_day]
      - date: datetime64[ns]
      - corridor: "RUB_TJS" | "RUB_UZS" | "RUB_KGS" | "RUB_AMD" | "RUB_KZT" | "RUB_USD" | "RUB_EUR" | "RUB_CNY"
      - rate: float — VunitRate из XML ЦБ (рублей за 1 единицу валюты)
      - is_trading_day: bool — False для выходных/праздников (forward-fill из предыдущего торгового дня)
    cutoff_date: если передан — строки после cutoff_date отбрасываются (no-lookahead).
    """

def save_rates(
    df: pd.DataFrame,
    path: str = "data/processed/rates.parquet",
) -> None:
    """Сохраняет DataFrame в parquet, создаёт директории при необходимости."""
```

**Источник данных:** `https://www.cbr.ru/scripts/XML_dynamic.asp`  
**Ключевое поле:** `VunitRate` — нормализован ЦБ к 1 единице валюты, устойчив к изменениям номинала.  
**CLI:** `python -m src.data.download` — скачивает и сохраняет `data/processed/rates.parquet`.

## src/indicators

```python
class BaseIndicator:
    name: str

    def compute(
        self,
        df: pd.DataFrame,
        corridor: str,
        cutoff_date: date,
    ) -> pd.Series:
        """
        Returns score series indexed by date.
        Score range: -1..1 or 0..1 (document per indicator).
        Must not use any data after cutoff_date.
        """

    def get_signal(
        self,
        df: pd.DataFrame,
        corridor: str,
        cutoff_date: date,
        threshold: float,
    ) -> bool:
        """Returns True if signal fires on cutoff_date."""
```

## src/backtest

```python
@dataclass
class BacktestResult:
    indicator: str
    corridor: str
    hit_rate: dict[int, float]    # {h_days: rate}
    lift: float                    # vs random day
    signal_count: int
    signals_per_week: float
    clustering_score: float        # 0=perfect spread, 1=all clustered
    cost_of_waiting_bps: float    # basis points lost waiting for slow signal

def run_walkforward(
    indicator: BaseIndicator,
    corridor: str,
    df: pd.DataFrame,
    train_years: int = 3,
    test_months: int = 6,
    h_horizons: list[int] = [1, 3, 5, 10, 20],
) -> BacktestResult: ...
```

## src/pipeline

```python
@dataclass
class Signal:
    date: date
    corridor: str
    indicator: str
    direction: str      # "favorable_now" | "window_closing"
    strength: float     # 0..1
    push_text: str

def generate_signals(
    cutoff_date: date,
    corridors: list[str] | None = None,
    cooldown_days: int = 3,
    max_per_week: int = 2,
) -> list[Signal]: ...
```
