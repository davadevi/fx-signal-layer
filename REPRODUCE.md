# Воспроизведение результатов

## Требования

```bash
pip install -r requirements.txt
```

## 1. Данные

```bash
python -m src.data.download    # скачать курсы ЦБ
python -m src.data.normalize   # нормализовать, записать в data/processed/rates.parquet
```

## 2. OOT-валидация (основные числа)

```bash
PYTHONPATH=. python scripts/run_oot_validation.py
```

Выводит таблицу in-sample lift / OOT lift / CI по 5 коридорам и горизонтам h=5,10,20.
Сохраняет `reports/oot_validation_{date}.json`.

Ожидаемые результаты (h=5, confirm_days=2):

| Коридор | IS Lift | CI нижняя | OOT Lift |
|---------|---------|-----------|----------|
| KGS | 1.60 | >1.07 | — |
| TJS | 1.48 | >1.07 | — |
| UZS | 1.22 | <1.0 | — |
| AMD | 1.41 | <1.0 | — |
| KZT | ~1.0 | <1.0 | — |

*OOT период: 2025-07-01 — конец данных. Мало сигналов (~5-7 на коридор), поэтому OOT lift нестабилен.*

## 3. Pipeline — один день

```bash
python -m src.pipeline.run --cutoff-date 2026-09-03
```

История сигналов сохраняется в `data/signal_history.json`. При повторном вызове cooldown учитывает предыдущие сигналы.

## 4. Бэктест конкретного индикатора

```python
import pandas as pd
from src.backtest.engine import run_walkforward
from src.indicators.log_return_percentile import LogReturnPercentileIndicator

df = pd.read_parquet("data/processed/rates.parquet")
result = run_walkforward(
    indicator=LogReturnPercentileIndicator(confirm_days=2),
    corridor="RUB_KGS",
    df=df,
    h_horizons=[5, 10, 20],
    ci_horizons=[5, 10, 20],
)
print(result.lift, result.lift_ci_low)
```

## 5. Тесты

```bash
make test
# 30 passed
```
