# FX Signal Layer — Описание проекта (промежуточная версия)

**Alfa-Bank Hackathon · Сентябрь 2026**

---

## Краткая аннотация

Система определяет дни с исторически выгодным курсом для трансграничных переводов по 5 коридорам (RUB → TJS, UZS, KGS, AMD, KZT) и генерирует push-уведомление клиенту. Основной индикатор — percentile rank 5-дневного log-return в скользящем окне 60 дней — устойчив к нестационарности курсового ряда и валидирован через walk-forward бэктест с bootstrap CI. На двух коридорах (KGS, TJS) достигнут lift > 1.4 с нижней границей CI > 1.0; частота сигналов при строгом пороге составляет 0.08–0.11 в неделю вместо целевых 1–2 — это открытый вопрос до финала.

---

## Проблематика

Трудовые мигранты, переводящие заработок домой, совершают 1–2 перевода в месяц по фиксированному коридору. Курс на дату перевода определяется удобством (зарплата поступила, время есть), а не выгодностью момента. На горизонте недели курс может колебаться на 1–3%, что при типичном переводе 30 000 ₽ составляет 300–900 ₽ потерь.

Приложение Альфа-Банка не предоставляет клиенту сигнал о выгодности текущего момента. Задача — восполнить этот пробел через push-уведомление, основанное на проверяемых статистических свойствах ряда курсов.

---

## Постановка задачи

**Цель:** на каждую торговую дату T определить, является ли текущий курс выгодным относительно исторического распределения, и при подтверждении отправить клиенту фактологическое push-уведомление.

### Целевые метрики

| Метрика | Значение |
|---------|----------|
| Lift над случайным днём | ≥ 1.3 устойчиво (pathwise, не только endpoint T+h) |
| Выгода в б.п. | > 0 на h=5 — отдельный критерий годности, независимый от lift |
| Частота сигналов | 1–2 / коридор / неделю |
| Горизонт оценки | h = 5 рабочих дней |
| Асимметрия ошибок | FP-вес = 3× (ложный сигнал дороже пропущенного) |
| Покрытие | 5 коридоров |

### Жёсткие ограничения

- **No lookahead:** сигнал на дату T использует только данные ≤ T. Курс ЦБ за день T публикуется на T-1 — учтено.
- **Compliance:** push-текст содержит только факты прошлого и настоящего. Запрещены предсказания, срочность, гарантии, инвестиционные формулировки.
- **Walk-forward only:** параметры обучаются на [start, T−gap], тест на [T−gap+1, T+window].

---

## Техническое решение

### Архитектура

```
CBR XML → src/data/ → src/indicators/ → src/backtest/
                              ↓
                         src/ml/ → src/pipeline/ → src/texts/ → Push
```

### Ключевые модули

| Модуль | Файлы | Назначение |
|--------|-------|-----------|
| `src/data/` | `download.py` | Загрузка CBR XML, нормализация VunitRate, forward-fill, parquet |
| `src/indicators/` | 10 файлов | BaseIndicator + 8 индикаторов; compute(df, cutoff_date) → Series[0..1] |
| `src/backtest/` | `engine.py`, `metrics.py` | Walk-forward, hit rate A/B, lift, CI bootstrap |
| `src/ml/` | `features.py`, `labels.py`, `train.py` | LightGBM, asymmetric loss FP×3, two-tier threshold |
| `src/pipeline/` | `signals.py`, `run.py` | Mandatory/optional tier, cooldown 3d, cap 2/week |
| `src/texts/` | `templates.py` | Compliance validator + push-текст formatter |

### Основной индикатор: LogReturnPercentile

Курсовой ряд I(1) — ненужен percentile по уровню. Используем log-return:

```
log_ret(t) = log(rate(t) / rate(t-1))
score(t)   = percentile_rank(log_ret(t), window=60d)
```

Сигнал при `score < 0.20` (текущий log-return ниже 80% наблюдений за 60 дней) с подтверждением на следующий день (`confirm_days=2`).

**Tier-логика:**
- `mandatory` (strong): confirm_days=2, strength = 1.0 − score
- `optional` (weak): confirm_days=0, strength = 0.5 × (1.0 − score)

**Подавление кризисного режима:** если `volatility_regime == 0.0` (30-дневная реализованная волатильность > 85-го перцентиля за год) — сигнал не генерируется.

### ML-слой

- Модель: LightGBM walk-forward (2y train / 3m test, embargo 5d, шаг квартал)
- Target: `is_local_min(t, h=5)` — был ли день t локальным минимумом в окне ±5 дней
- Фичи: 10 колонок (log-return rank, rsi, volatility regime, bollinger z-score, calendar)
- Асимметричный loss: FP-вес = 3.0
- Two-tier threshold: t\_mandatory = quantile(0.90), t\_optional = quantile(0.67)

---

## Реализованные компоненты

| Компонент | Файлы | Статус |
|-----------|-------|--------|
| Данные + нормализация | `src/data/download.py` | ✓ Завершён |
| BaseIndicator | `src/indicators/base.py` | ✓ Завершён |
| LogReturnPercentile | `src/indicators/log_return_percentile.py` | ✓ Завершён |
| VolatilityRegime | `src/indicators/volatility_regime.py` | ✓ Завершён |
| RSI, Bollinger, Calendar | `src/indicators/rsi.py` и др. | ✓ Завершён |
| Combo indicators | `src/indicators/combo_log_return.py` и др. | ✓ Завершён |
| Walk-forward engine | `src/backtest/engine.py` | ✓ Завершён |
| Metrics (lift, CI, clustering) | `src/backtest/metrics.py` | ✓ Завершён |
| ML features + labels | `src/ml/features.py`, `labels.py` | ✓ Завершён |
| LightGBM train | `src/ml/train.py` | ✓ Завершён |
| Signal pipeline | `src/pipeline/signals.py` | ✓ Завершён |
| Push-текст + compliance | `src/texts/templates.py` | ✓ Завершён |
| Unit-тесты (25 шт.) | `tests/unit/` | ✓ Завершён |
| No-lookahead тесты | `tests/unit/test_no_lookahead.py` | ✓ Завершён |
| EDA notebook | `notebooks/01-eda-data-pipeline.ipynb` | ✓ Завершён |
| Интеграционные тесты | `tests/integration/test_end_to_end.py` | ◑ Частично |
| REPRODUCE.md | `docs/REPRODUCE.md` | ✗ Planned |
| PILOT.md | `docs/PILOT.md` | ✗ Planned |
| LIMITATIONS.md | `docs/LIMITATIONS.md` | ✗ Planned |

---

## Предварительные результаты

### Базовая модель (PercentileRank по абсолютному уровню)

Lift < 1.0 на всех коридорах (0.86–0.97). Причина: курсовой ряд I(1), percentile по уровню теоретически некорректен.

### Основная модель (LogReturnPercentile, confirm_days=2, h=5)

| Коридор | Lift h=5 | CI 90% | Сигн./нед | Статус |
|---------|----------|--------|-----------|--------|
| RUB/KGS | 1.60 | [1.07, 1.60] | 0.09 | ✓ CI > 1.0 |
| RUB/TJS | 1.48 | [1.07, 1.48] | 0.11 | ✓ CI > 1.0 |
| RUB/AMD | 1.41 | [0.80, 1.41] | 0.08 | ⚠ CI < 1.0 |
| RUB/UZS | 1.22 | [0.76, 1.22] | 0.11 | ⚠ CI < 1.0 |
| RUB/KZT | 1.01 | [0.50, 1.01] | 0.10 | ✗ Нет сигнала |

CI рассчитан методом circular block bootstrap (2000 resample, 90-дневные блоки).

### Стабильность по горизонтам (KGS, лучший коридор)

| Горизонт | Lift | CI нижняя |
|----------|------|-----------|
| h = 1 | 1.12 | 0.65 |
| h = 3 | 1.38 | 0.93 |
| h = 5 | 1.60 | 1.07 |
| h = 10 | 1.68 | 1.08 |
| h = 20 | 1.71 | — |

Lift растёт с горизонтом — сигнал более точен на среднесрочном окне.

---

## Ограничения и открытые вопросы

### Подтверждённые ограничения

1. **Hit definition — endpoint vs pathwise:** текущий бэктест использует endpoint (`rate[t+h] >= rate[t]`). Продуктовый критерий — pathwise: курс не хуже ни в один из дней T+1..T+h. Это разные метрики; наши цифры lift рассчитаны по endpoint.

2. **bps отрицательные:** hit rate > 50% на KGS/TJS подтверждён, но средняя выгода в базисных пунктах на h=5 отрицательна по всем коридорам — сигнал приходит после того, как выгодное движение состоялось. По продуктовому определению это означает, что метод пока не готов к пилоту.

3. **Частота:** 0.08–0.11 сигн./нед при confirm_days=2 — в 10× ниже цели 1–2. Точность и частота в trade-off.

4. **Бэктест ≠ runtime:** логика фильтрации в `engine.py` и в `generate_signals()` реализована по-разному. Метрики бэктеста нельзя напрямую экстраполировать на продакшн.

5. **OOT валидация:** выбор параметров (порог, window) проводился по агрегированным результатам — истинный out-of-time тест на нетронутых данных не завершён.

### Открытые вопросы

- Оптимальный threshold для weak-tier (confirm_days=0): как сбалансировать frequency и precision?
- Нужен ли ML-слой поверх правилового индикатора, или он избыточен при confirm_days=2?
- Как учесть корреляцию между коридорами (TJS/UZS/KGS/AMD коррелируют 0.83–0.97 с USD/RUB) для дедупликации сигналов?

---

## План работ до финальной версии

| Срок | Задачи |
|------|--------|
| 4–5 сент. | Синхронизация backtest↔runtime; OOT валидация pathwise; тест weak-tier по частоте |
| 6 сент. | Интеграционные тесты; REPRODUCE.md; PILOT.md; LIMITATIONS.md |
| 7 сент. | Финальный отчёт; демо pipeline; финальная презентация |

---

## Команда и распределение задач

| Участник | Роль | Выполненные задачи | Участие |
|----------|------|--------------------|---------|
| **Давид Гусейнов** | ML Engineer | Данные (download.py, нормализация, parquet); индикаторы (8 вариантов, LogReturnPercentile); backtest engine и metrics; ML pipeline (features, labels, train.py) | 33% |
| **София** | Product Manager | Продуктовая гипотеза и портрет пользователя; 6 ADR-документов; compliance-требования к push-текстам; документация (PIPELINE.md, interfaces.md, iteration logs) | 33% |
| **Варя** | Data Engineer | Signal pipeline (generate_signals, mandatory/optional tier, cooldown); push-текст шаблоны + compliance validator; 25 unit-тестов + no-lookahead suite; валидационный отчёт и lift tables | 33% |

---

## Стек технологий

- **Язык:** Python 3.11+
- **Данные:** pandas, pyarrow, CBR XML API
- **ML:** LightGBM, scikit-learn
- **Тесты:** pytest (25 unit + integration)
- **Статистика:** circular block bootstrap, ADF test (statsmodels), PELT (ruptures)
- **CI:** asymmetric loss, 90% confidence level
- **Документация:** 6 ADR + PIPELINE.md (404 строки) + 3 iteration log
