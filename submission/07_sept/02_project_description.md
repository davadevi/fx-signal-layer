# FX Signal Layer — Описание проекта

**Alfa-Bank Hackathon · Сентябрь 2026**

---

## Краткая аннотация

Система определяет дни с исторически выгодным курсом для трансграничных переводов по 5 коридорам (RUB → TJS, UZS, KGS, AMD, KZT) и генерирует push-уведомление клиенту. Основной индикатор — percentile rank 5-дневного log-return в скользящем окне 60 дней — устойчив к нестационарности курсового ряда и валидирован через walk-forward бэктест с bootstrap CI и независимым OOT-периодом (с 2025-07-01). На трёх коридорах (KGS, TJS, AMD) достигнут lift > 2.0 с OOT-подтверждением и нижней границей CI > 1.15.

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
| Выгода в б.п. | > 0 на h=5 — отдельный критерий годности |
| Частота сигналов | 1–2 / коридор / неделю |
| Горизонт оценки | h = 5, 10 рабочих дней |
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
| `src/backtest/` | `engine.py`, `metrics.py` | Walk-forward, hit rate pathwise, lift, CI bootstrap |
| `src/ml/` | `features.py`, `labels.py`, `train.py` | LightGBM, asymmetric loss FP×3 (не используется в финальном pipeline) |
| `src/pipeline/` | `signals.py`, `run.py` | confirm_days=2, stateful cooldown 3d, compliance validator |
| `src/texts/` | `templates.py` | Compliance validator + push-текст formatter |

### Основной индикатор: LogReturnPercentile

Курсовой ряд I(1) — percentile по уровню некорректен. Используем log-return:

```
log_ret(t) = log(rate(t) / rate(t-1))
score(t)   = percentile_rank(log_ret(t), window=60d)
```

Сигнал при `score < 0.20` (текущий log-return ниже 80% наблюдений за 60 дней) с подтверждением два дня подряд (`confirm_days=2`). Подавление кризисного режима: если реализованная волатильность > 85-го перцентиля за год — сигнал не генерируется.

### ML-слой

Обучен (LightGBM, asymmetric loss FP×3), но в финальный pipeline не включён: на OOT-данных чистый индикатор (lift 2.1–2.5) устойчивее ML-слоя (lift деградирует до 1.0–1.4). Код сохранён в `src/ml/` для дальнейших экспериментов.

---

## Реализованные компоненты

| Компонент | Файлы | Статус |
|-----------|-------|--------|
| Данные + нормализация | `src/data/download.py` | ✓ Завершён |
| BaseIndicator | `src/indicators/base.py` | ✓ Завершён |
| LogReturnPercentile | `src/indicators/log_return_percentile.py` | ✓ Завершён |
| VolatilityRegime | `src/indicators/volatility_regime.py` | ✓ Завершён |
| RSI, Bollinger, Calendar | `src/indicators/rsi.py` и др. | ✓ Завершён |
| Walk-forward engine | `src/backtest/engine.py` | ✓ Завершён |
| Metrics (pathwise lift, CI) | `src/backtest/metrics.py` | ✓ Завершён |
| ML features + labels | `src/ml/features.py`, `labels.py` | ✓ Завершён |
| LightGBM train | `src/ml/train.py` | ✓ Завершён |
| Signal pipeline | `src/pipeline/signals.py` | ✓ Завершён |
| Stateful cooldown | `src/pipeline/run.py` | ✓ Завершён |
| Push-текст + compliance | `src/texts/templates.py` | ✓ Завершён |
| OOT validation script | `scripts/run_oot_validation.py` | ✓ Завершён |
| Unit-тесты (30 шт.) | `tests/unit/` | ✓ Завершён |
| No-lookahead тесты | `tests/unit/test_no_lookahead.py` | ✓ Завершён |
| REPRODUCE.md | `REPRODUCE.md` | ✓ Завершён |
| LIMITATIONS.md | `LIMITATIONS.md` | ✓ Завершён |
| Pilot Design | `submission/07_sept/05_pilot_design.md` | ✓ Завершён |

---

## Результаты — OOT-валидация

Hit definition: **pathwise** — курс не хуже ни в один из дней T+1..T+h.
OOT-период: 2025-07-01 и позже (нетронутые данные, не использовались при отборе параметров).
CI: circular block bootstrap, 2000 resample, 90-дневные блоки.

### Финальные результаты

| Коридор | h | IS Lift | OOT Lift | CI 90% ↓ | Сигн./нед | Статус |
|---------|---|---------|----------|-----------|-----------|--------|
| RUB/KGS | 5 | 2.10 | 1.84 | 1.36 | 0.057 | ✓ CI > 1.0 |
| RUB/KGS | 10 | 2.17 | 2.24 | 1.15 | 0.057 | ✓ CI > 1.0 |
| RUB/TJS | 5 | 2.35 | 1.76 | 1.76 | 0.065 | ✓ CI > 1.0 |
| RUB/TJS | 10 | 2.52 | 2.13 | 1.65 | 0.065 | ✓ CI > 1.0 |
| RUB/AMD | 10 | 2.81 | 2.16 | 1.30 | 0.033 | ✓ CI > 1.0 |
| RUB/UZS | 5–20 | 1.2–1.9 | 1.0–1.3 | < 1.0 | 0.065 | ✗ CI не проходит |
| RUB/KZT | все | ~1.1 | NaN | < 1.0 | 0.033 | ✗ Нет OOT сигналов |

Базовая модель (PercentileRank по абсолютному уровню курса): lift 0.86–0.97 — хуже случайного.

---

## Ограничения

1. **Частота:** 0.033–0.065 сигн./нед при confirm_days=2 — в 15–30× ниже цели 1–2. Частота и точность в trade-off.

2. **bps на h=5 отрицательный:** hit rate подтверждён, но средняя выгода в базисных пунктах на h=5 отрицательна — сигнал приходит после выгодного движения. На h=10/20 bps улучшается.

3. **AMD — малая выборка:** N=4 сигнала в OOT-периоде. Статистическая устойчивость требует накопления в реальном пилоте.

4. **KZT, UZS:** не проходят CI ни на одном горизонте. В пилот не включены.

5. **ML-слой исключён из production:** на OOT деградирует. Требует дополнительных экспериментов с feature engineering.

---

## Команда и распределение задач

| Участник | Роль | Выполненные задачи | Участие |
|----------|------|--------------------|---------|
| **Давид Гусейнов** | ML Engineer | Данные (download.py, нормализация, parquet); индикаторы (8 вариантов, LogReturnPercentile); backtest engine и metrics; ML pipeline (features, labels, train.py); OOT validation; stateful cooldown | 33% |
| **София** | Product Manager | Продуктовая гипотеза и портрет пользователя; 6 ADR-документов; compliance-требования к push-текстам; документация (PIPELINE.md, interfaces.md, iteration logs); Pilot Design | 33% |
| **Варя** | Data Engineer | Signal pipeline (generate_signals, cooldown); push-текст шаблоны + compliance validator; 30 unit-тестов + no-lookahead suite; REPRODUCE.md; LIMITATIONS.md | 33% |

---

## Стек технологий

- **Язык:** Python 3.11+
- **Данные:** pandas, pyarrow, CBR XML API
- **ML:** LightGBM, scikit-learn
- **Тесты:** pytest (30 unit + integration)
- **Статистика:** circular block bootstrap, ADF test (statsmodels), PELT (ruptures)
- **CI:** asymmetric loss, 90% confidence level
- **Документация:** 6 ADR + PIPELINE.md + REPRODUCE.md + LIMITATIONS.md
