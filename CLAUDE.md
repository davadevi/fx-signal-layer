# Project: FX Signal Layer — Alfa-Bank Hackathon

## Goal
Build signal layer for cross-border transfers (RUB → TJS/UZS/KGS/AMD/KZT).
Output: push notification trigger when exchange rate is favorable.
Target: lift ≥ 1.3 over random day, 1–2 signals/corridor/week.

## Hard Constraints (NEVER violate)

### No Lookahead
Signal on date T must use ONLY data available on T.
- CBR rate for day T is published on T-1 (sutnochny lag) — account for this.
- Walk-forward only: train on [start, T-gap], test on [T-gap+1, T+window].
- Any metric computed with future data = disqualified.
- Every module must accept `cutoff_date` param and filter data to `<= cutoff_date`.

### Signal Frequency
- Target: 1–2 signals per corridor per week.
- Indicator firing 30+ times/month = unusable regardless of accuracy.
- Cooldown between signals: configurable, default 3 days per corridor.

### Compliance — Push Text Rules
ALLOWED (facts about past/present only):
- "Курс сомони снижается четвёртый день подряд"
- "Сейчас курс выгоднее, чем в 85% дней за последние три месяца"
- "За неделю рубль укрепился к сому на 2,1%"

FORBIDDEN (predictions, promises, urgency):
- "Курс скоро вырастет" — prediction
- "Успейте, пока не подорожало" — urgency = implicit prediction
- "Гарантируем лучший курс" — promise
- "Заработайте на курсе" — investment advice framing

### Error Asymmetry
False positive (said "good rate" → rate got worse) costs MORE than false negative (missed good day).
All thresholds and loss functions must reflect this asymmetry.

## Architecture

### Module Contracts

**`src/data/`** — data loading and normalization
- Input: CBR XML/CSV feeds
- Output: `pd.DataFrame` with columns `[date, corridor, rate_normalized]`
- Corridors: RUB_TJS, RUB_UZS, RUB_KGS, RUB_AMD, RUB_KZT
- Weekend/holiday gaps: forward-fill, flag with `is_trading_day: bool`
- Denomination normalization: divide raw rate by nominal (TJS=10, UZS=1000, KGS=10, AMD=100, KZT=1)

**`src/indicators/`** — signal indicators
- Each indicator: separate file, inherits `BaseIndicator`
- Interface: `indicator.compute(df, cutoff_date) -> pd.Series[float]` (score -1..1 or 0..1)
- Indicators: momentum, percentile_level, reversal, seasonality + custom
- Must handle forward-fill artifacts (don't count weekend non-changes as momentum)

**`src/backtest/`** — walk-forward backtesting engine
- Interface: `backtest(indicator, corridor, train_years=3, test_months=6) -> BacktestResult`
- Metrics: hit_rate@h (h=1,3,5,10,20), lift_over_random, signal_frequency, signal_clustering
- Output: saves report to `reports/{indicator}_{corridor}_{date}.json`

**`src/ml/`** — ML models on top of indicator features
- Target: `is_local_min(t, h)` — was day t a local min in window ±h days
- Features: derived from indicators
- Models: logistic regression (baseline), LightGBM
- Loss: asymmetric (FP penalty > FN penalty)

**`src/pipeline/`** — combine indicators into single signal stream
- Input: scores from all indicators
- Output: `Signal(date, corridor, indicator, direction, strength, scenario, push_text)`
- Applies cooldown, deduplication, frequency cap

**`src/texts/`** — push text templates
- Map: `(indicator_type, direction) -> push_text_template`
- All templates validated against compliance rules

### Key Data Types
```python
@dataclass
class Signal:
    date: date
    corridor: str          # "RUB_TJS"
    indicator: str         # "momentum"
    direction: str         # "favorable_now" | "window_closing"
    strength: float        # 0..1
    push_text: str

@dataclass  
class BacktestResult:
    indicator: str
    corridor: str
    hit_rate: dict[int, float]   # {h: rate}
    lift: float
    signal_count: int
    clustering_score: float
```

## Project Structure
```
data/raw/          # downloaded CBR data — do not modify
data/processed/    # normalized time series
src/data/          # data loading, normalization
src/indicators/    # each indicator as separate module
src/backtest/      # walk-forward engine + metrics
src/ml/            # ML models
src/pipeline/      # signal combiner
src/texts/         # push templates
tests/unit/        # unit tests per module
tests/integration/ # end-to-end signal generation tests
notebooks/         # EDA only — no production code in notebooks
reports/           # backtest results (JSON + plots)
docs/decisions/    # ADR files
docs/api/          # module interface specs
```

## Development Rules
- Feature branches only: `feature/`, `fix/`, `exp/`
- No direct commits to `main` or `develop`
- PR requires: tests pass + backtest results attached (if backtest touched)
- No notebooks in production pipeline — extract to `src/` first
- Type hints required on all public functions
- `make test` must pass before every PR

## AI Tools

### graphify
Запускать после того как `src/` наберёт 10+ файлов.
```
/graphify src/          # построить граф кодовой базы
/graphify docs/         # граф решений и интерфейсов
graphify query "где используется cutoff_date"
graphify path "BaseIndicator" "BacktestResult"
graphify explain "walk-forward"
```
Граф живёт в `graphify-out/`. После правок кода: `graphify update .`

### cavecrew agents
Три специализированных агента — вызывать через Agent tool:

| Агент | Когда |
|-------|-------|
| `caveman:cavecrew-investigator` | "где определён X", "что вызывает Y" — read-only |
| `caveman:cavecrew-builder` | хирургическая правка 1–2 файлов |
| `caveman:cavecrew-reviewer` | review PR перед merge, одна строка на проблему |

**Обязательно:** каждый PR прогнать через `cavecrew-reviewer` до merge.  
Главное что ловить: lookahead, неверный baseline, нарушение контрактов модулей.

### /review (caveman-review)
Перед merge в `develop` — запустить `/review` на diff.  
Ловит: lookahead паттерны, нарушения no-lookahead правила, dead code.

### Iteration log
Каждый эксперимент с индикатором = запись в `docs/iterations/*/log.md`.  
Формат — см. заголовок log.md файла.  
Отрицательный результат логировать так же как положительный.

### Bug review log
Читать `docs/dev/bug-review-log.md` перед любой фичей или фиксом.  
Писать туда после каждого найденного бага.

## Documentation
| Файл | Содержание |
|------|-----------|
| `docs/api/interfaces.md` | Контракты всех модулей (SSOT) |
| `docs/decisions/ADR-001` | Выбор источника данных |
| `docs/decisions/ADR-002` | Q&A с заказчиком — сессия 1 |
| `docs/decisions/ADR-003` | Q&A с заказчиком — сессия 2 + таблица допущений |
| `docs/iterations/` | Iteration logs по каждому блоку |
| `docs/dev/bug-review-log.md` | Лог багов — читать перед фичей |
