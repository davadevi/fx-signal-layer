# Pipeline: как работает сигнальный слой

> Обновлять при каждом изменении архитектуры, порогов, логики классификации или добавлении индикатора.

**Последнее обновление:** 2026-09-03  
**Актуальная ветка:** `develop`

---

## Обзор

```
CBR XML/CSV
    │
    ▼
rates.parquet          ← нормализованные курсы ЦБ, все коридоры
    │
    ├──► Индикаторы    ← вычисляют score per day, no-lookahead
    │        │
    │        ▼
    │   build_features()  ← 10 признаков для ML
    │        │
    │        ▼
    │   LightGBM → P(hit)   ← вероятность «сейчас выгодно»
    │
    └──► generate_signals(cutoff_date)
              │
              ▼
         [Signal, ...]   ← mandatory / optional, с push_text
```

Hit-правило: сигнал на день `t` = "попадание" если `rate[t+h] >= rate[t]`  
(курс не стал лучше → клиент был прав, что перевёл именно в этот день).  
Меньший курс = выгоднее для отправителя (рублей за единицу иностранной валюты).

---

## Шаг 1 — Данные (`src/data/`)

**Вход:** выгрузки ЦБ РФ (XML/CSV) → `data/raw/`  
**Выход:** `data/processed/rates.parquet`

| Колонка | Тип | Описание |
|---------|-----|----------|
| `date` | datetime64 | Дата |
| `corridor` | str | `RUB_TJS` / `RUB_UZS` / `RUB_KGS` / `RUB_AMD` / `RUB_KZT` |
| `rate` | float | Рублей за единицу иностранной валюты (нормализовано) |
| `is_trading_day` | bool | False = выходной, курс = ffill от предыдущего торгового дня |

**Нормализация номинала:** `rate = VunitRate / nominal`

| Валюта | Nominal |
|--------|---------|
| TJS | 10 |
| UZS | 1000 |
| KGS | 10 |
| AMD | 100 |
| KZT | 1 |

**Обучающее окно:** с `2022-04-01` (после структурного перелома февраль–март 2022).  
Данные до 2022 — другой режим волатильности, не используются.

---

## Шаг 2 — Индикаторы (`src/indicators/`)

### Контракт

```python
class BaseIndicator:
    name: str
    threshold: float

    def compute(self, df: pd.DataFrame, corridor: str, cutoff_date: date) -> pd.Series:
        """Score per calendar day. No data after cutoff_date."""
        filtered = self._filter(df, corridor, cutoff_date)  # ПЕРВЫМ — no-lookahead
        ...
```

`compute()` возвращает `pd.Series` с daily index (включая выходные, ffill), значения в `[0, 1]` или raw Z-score.

### Текущие индикаторы

#### `LogReturnPercentileIndicator` ← основной сигнал

```
log_ret[t] = log(rate[t] / rate[t-return_window])

Параметры по умолчанию: return_window=5, rank_window=60, threshold=0.20

score[t] = rank log_ret[t] среди предыдущих rank_window значений
         = (кол-во значений строго меньше log_ret[t]) / (rank_window - 1)
```

- `score < 0.20` → рубль укрепился сильнее, чем в 80% последних 60 дней
- `confirm_days=2`: дополнительно требует `rate[t] > rate[t-1] > rate[t-2]` (разворот подтверждён)
- Лог-доходность I(0) — статионарна, в отличие от уровня курса (I(1))

**Варианты:**

| Вариант | confirm_days | lift@5 (TJS/KGS/AMD) | sig/wk |
|---------|-------------|----------------------|--------|
| c0 | 0 | 1.05–1.13 | ~0.48 |
| c2 | 2 | 1.42–1.62 ✅ | ~0.09 |

#### `VolatilityRegimeFilter`

```
30d realized vol = std(log_returns) * sqrt(252)
score = 1.0 если vol < 85-й перцентиль 252d rolling vol (calm)
      = 0.0 если crisis
```

Crisis → все сигналы подавляются.

#### `RSIFilter`

```
RSI(14) по Wilder (EWM сглаживание)
score = RSI / 100 ∈ [0, 1]
signal когда score < 0.35 (RSI < 35 = перепроданность)
```

Используется как дополнительный признак (ML) и опциональный фильтр (`require_rsi=True`).

#### `PercentileRankIndicator`

```
score = rolling 30d percentile rank уровня курса
```

⚠️ Применяется к I(1) ряду — не используется как самостоятельный сигнал (lift < 1.0).
Оставлен как контекстный признак и для сравнения.

#### `BollingerZScoreIndicator`

```
z = (rate - MA20) / std20
score = raw z-score (отрицательный = курс ниже MA)
signal когда z < -1.5
```

Показал слабые результаты (lift 0.76–1.07) на текущих данных. Используется как ML-признак.

#### `CalendarSeasonalityIndicator`

```
score = 0.0 (favorable) если:
  - день месяца 20–28 (налоговый период: экспортёры продают валюту → RUB крепнет)
  - месяц июль–октябрь И коридор TJS/UZS/KGS (пик сезонных переводов)
score = 1.0 иначе
```

Как фильтр через AND с log_ret_c0: +5–9% lift на миграционных коридорах.  
Standalone: слишком частый (1.07 сиг/нед), lift 1.08–1.14.

#### `AndLogRetCalendarIndicator`

```
score = log_ret_c0 score   если calendar score < 0.5 (favorable day)
      = NaN                иначе
```

Lift 1.15–1.18 на TJS/KGS, sig/wk ~0.30.

#### `CombinedLogReturnIndicator`

```
score < 0.20  → strong tier (confirm=2 fired)
0.20–0.40    → weak tier  (confirm=0 fired, confirm=2 did not)
>= 0.40      → no signal
```

OR-комбинация confirm=2 и confirm=0. Lift ~1.1, sig/wk ~0.49.

---

## Шаг 3 — Бэктест (`src/backtest/`)

### Walk-forward методология

```
Время ─────────────────────────────────────────────────────────►

[═══════════ Train 2y ═══════════][ 5d ][══ Test 3m ══]
                  [═══════════ Train 2y ═══════════][ 5d ][══ Test 3m ══]
                                    ...

TRAIN_START = 2022-04-01
train_years = 2, test_months = 3, embargo_days = 5, step = quarterly
```

- **Embargo:** первые 5 дней test-окна пропускаются при извлечении сигналов (нет утечки лейблов)
- **OOT:** окна после `2024-01-01` выделяются отдельно — проверка устойчивости

### Метрики

```python
# Definition A (основная)
hit_rate_A@h = P(rate[t+h] >= rate[t]) на сигнальных днях

# Definition B (теоретически строже)
hit_rate_B@h = P(rate[t] < mean(rate[t+1..t+h])) на сигнальных днях

# Base rate = те же метрики на ВСЕХ торговых днях (случайный базис)
lift@h = hit_rate@h / base_rate@h    # цель: >= 1.3

# Bootstrap CI (n=2000 ресэмплов, alpha=0.05) — только для h=5
# Статзначимость: CI нижняя граница > 1.0
```

---

## Шаг 4 — ML-слой (`src/ml/`)

### Построение признаков (`src/ml/features.py`)

```python
build_features(df, corridor, cutoff_date) -> pd.DataFrame  # 10 колонок
```

| Признак | Источник |
|---------|---------|
| `log_ret_c0` | LogReturnPercentile(confirm=0).compute() score |
| `log_ret_c2` | LogReturnPercentile(confirm=2).compute() score, NaN если не подтверждён |
| `pct_rank` | PercentileRankIndicator().compute() score |
| `rsi` | RSIFilter().compute() score (RSI/100) |
| `regime` | VolatilityRegimeFilter().compute() (0.0/1.0) |
| `bollinger_z` | BollingerZScoreIndicator().compute() raw z |
| `calendar` | CalendarSeasonalityIndicator().compute() (0.0/1.0) |
| `log_ret_c0_lag1` | log_ret_c0 сдвиг на 1 торговый день |
| `log_ret_c0_lag2` | сдвиг на 2 торговых дня |
| `pct_rank_lag1` | pct_rank сдвиг на 1 торговый день |

Все признаки вычисляются с `cutoff_date = train_end` для обучения, `cutoff_date = test_end` для теста.

### Целевая переменная (`src/ml/labels.py`)

```python
make_labels(df, corridor, h=5) -> pd.Series
# y[t] = 1 если rate[t+5] >= rate[t], иначе 0
# Вычисляется на ПОЛНОМ df (без cutoff) — только для тренировочных лейблов
```

### Обучение

```python
# Асимметричные веса: ложноположительный сигнал стоит дороже
sample_weight = np.where(y_train == 1, 1.0, FP_WEIGHT)  # FP_WEIGHT = 3.0

model = LGBMClassifier(
    objective="binary", n_estimators=200, learning_rate=0.05,
    num_leaves=15, min_child_samples=5,
    feature_fraction=0.8, bagging_fraction=0.8, random_state=42,
)
model.fit(X_train, y_train, sample_weight=sample_weight)
```

### Двухзонная классификация

Пороги вычисляются из `train_probs` (только тренировочные предсказания — no-lookahead):

```python
t_mandatory = quantile(train_probs, 0.90)   # top 10% → mandatory
t_optional  = quantile(train_probs, 0.67)   # top 33% → optional
# Гарантия: t_optional < t_mandatory (fallback: t_opt = t_mand * 0.95)
```

| Зона | Условие | Cooldown | Lift@5 (avg) |
|------|---------|----------|-------------|
| **Mandatory** | `prob >= t_mandatory AND regime > 0` | ❌ не применяется | 1.15–1.66 |
| **Optional** | `t_opt <= prob < t_mand AND regime > 0` | ✅ 3 дня | 0.73–1.44 |
| None | `prob < t_optional OR regime == 0` | — | — |

### Результаты ML (walk-forward, FP_weight=3.0)

| Коридор | mand_lift@5 | opt_lift@5 | mand/wk | opt/wk |
|---------|------------|------------|---------|--------|
| RUB_KGS | 1.347 | 1.443 | 0.18 | 0.21 |
| RUB_AMD | 1.657 ✅ | 0.798 | 0.18 | 0.27 |
| RUB_UZS | 1.441 ✅ | 0.730 | 0.27 | 0.31 |
| RUB_KZT | 1.239 | 1.181 | 0.23 | 0.15 |
| RUB_TJS | 1.152 | 1.036 | 0.27 | 0.27 |

---

## Шаг 5 — Signal Pipeline (`src/pipeline/signals.py`)

```python
generate_signals(
    cutoff_date: date,
    df: pd.DataFrame | None = None,   # если None — читает из rates.parquet
    corridors: list[str] | None = None,
    cooldown_days: int = 3,
    max_per_week: int = 2,
    require_rsi: bool = False,
) -> list[Signal]
```

### Алгоритм

```
для каждого коридора:

  1. compute() всех индикаторов с cutoff = cutoff_date

  2. regime == crisis?  →  skip (подавить оба типа)

  3. strong_ind (confirm=2) score < 0.20?
       → Signal(tier="mandatory", strength=1.0 - score)
         indicator="log_return_percentile_strong"

  4. elif weak_ind (confirm=0) score < 0.20?
       → Signal(tier="optional", strength=0.5 * (1.0 - score))
         indicator="log_return_percentile_weak"

  5. если require_rsi=True и RSI score > 0.35 → skip optional

mandatory_signals = все mandatory (без cap, без cooldown)

optional_slots = max(0, max_per_week - len(mandatory_signals))
optional_candidates — сортировать по strength desc
optional_kept = cooldown_filter(optional_candidates, cooldown_days=3,
                                prior=mandatory_signals)[:optional_slots]

return mandatory_signals + optional_kept
```

### Структура `Signal`

```python
@dataclass
class Signal:
    date: date
    corridor: str          # "RUB_KGS"
    indicator: str         # "log_return_percentile_strong" | "log_return_percentile_weak"
    direction: str         # "favorable_now"
    strength: float        # 0..1 (mandatory ~0.8-1.0, optional ~0.4-0.5)
    push_text: str         # готовый текст пуш-уведомления
    percentile_rank: float # score PercentileRankIndicator (контекст)
    rsi_score: float|None  # RSI/100 (контекст)
    regime: str            # "calm" | "crisis"
    tier: str              # "mandatory" | "optional"
```

### Push-текст (`src/texts/templates.py`)

```python
format_push_text(corridor, percentile_rank, current_rate, direction) -> str
```

**Разрешено:** факты о прошлом/настоящем  
**Запрещено:** прогнозы, срочность, гарантии, инвестиционные советы

Пример: `"Курс сома выгоднее, чем в 82% дней за последние 30 дней. Текущий курс: 1.0823"`

---

## CLI

```bash
# Сигналы на конкретную дату
python -m src.pipeline.run --cutoff-date 2024-06-15

# Бэктест одного индикатора
python -c "
from src.backtest.engine import run_walkforward
from src.indicators.log_return_percentile import LogReturnPercentileIndicator
import pandas as pd
df = pd.read_parquet('data/processed/rates.parquet')
ind = LogReturnPercentileIndicator(confirm_days=2)
r = run_walkforward(ind, 'RUB_TJS', df, save_report=False, compute_ci=False)
print(r.lift)
"
```

---

## Лучшие результаты по коридорам

| Коридор | Лучший индикатор | Lift@5 | CI 95% | Sig/wk | Цель ≥ 1.3 |
|---------|-----------------|--------|--------|--------|------------|
| RUB_KGS | log_ret_c2 | 1.616 | [1.077, 1.975] | 0.09 | ✅ CI > 1.0 |
| RUB_TJS | log_ret_c2 | 1.493 | [1.086, 1.900] | 0.11 | ✅ CI > 1.0 |
| RUB_AMD | log_ret_c2 | 1.418 | [0.803, 2.007] | 0.08 | ✅ |
| RUB_UZS | ML mandatory | 1.441 | — | 0.27 | ✅ |
| RUB_KZT | log_ret_c0 | 1.101 | — | 0.51 | ❌ |

**Ограничение:** log_ret_c2 даёт 0.08–0.11 сигнала/нед — ниже production target 1–2/нед.

---

## Что обновлять при изменениях

| Изменение | Что обновить в этом файле |
|-----------|--------------------------|
| Новый индикатор | Раздел «Текущие индикаторы», таблица результатов |
| Новый порог или параметр | Таблица вариантов соответствующего индикатора |
| Изменение логики классификации (mandatory/optional) | Раздел «Двухзонная классификация» |
| Новые метрики бэктеста | Раздел «Метрики» |
| Новые признаки ML | Таблица признаков |
| Новый коридор | Таблица результатов, таблица CLI-примеров |
| Изменение push-текста | Раздел «Push-текст» |
