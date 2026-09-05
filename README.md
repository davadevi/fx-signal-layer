# FX Signal Layer — Alfa-Bank Hackathon

Сигнальный слой для триггерных коммуникаций по трансграничным переводам.  
Детектирует выгодный момент курса RUB → TJS/UZS/KGS/AMD/KZT и генерирует пуш-уведомление.

## Задача

Клиент переводит деньги семье в страну СНГ. Разница курса внутри месяца — до 9%. Банк отправляет пуш когда момент статистически выгоднее обычного. Клиент решает сам — переводить сейчас или нет.

## Стек

Python 3.11+, pandas, LightGBM, scikit-learn, scipy, pytest

## Быстрый старт

```bash
git clone https://github.com/davadevi/fx-signal-layer.git
cd fx-signal-layer

pip install uv
uv sync --extra dev
pre-commit install

make data        # скачать и нормализовать курсы ЦБ
make test        # запустить тесты
make backtest    # прогнать walk-forward по всем коридорам
make signals-today  # сигналы на сегодня
```

## Структура

```
src/
  data/        # загрузка и нормализация курсов ЦБ
  indicators/  # индикаторы: momentum, percentile, reversal, seasonality
  backtest/    # walk-forward engine + метрики
  ml/          # LightGBM-модели на признаках индикаторов
  pipeline/    # комбинирование сигналов в единый поток
  texts/       # шаблоны пуш-уведомлений
docs/
  decisions/   # ADR: решения, Q&A с заказчиком, допущения команды
  iterations/  # лог экспериментов по каждому блоку
  api/         # контракты модулей
reports/       # результаты бэктестов
```

## Коридоры

| Коридор | Валюта |
|---------|--------|
| RUB_TJS | Таджикский сомони |
| RUB_UZS | Узбекский сум |
| RUB_KGS | Киргизский сом |
| RUB_AMD | Армянский драм |
| RUB_KZT | Казахстанский тенге |

## Целевые метрики

- Lift ≥ 1.3 над случайным торговым днём
- Hit rate по горизонтам h = 1/3/5/10/20 дней
- 1–2 сигнала на коридор в неделю, без кластеризации

## Ключевое ограничение

**No lookahead.** Сигнал на дату T считается только по данным ≤ T.  
Любое нарушение = дисквалификация результата.

## Git-флоу

- `main` — защищён, только через PR с апрувом
- `develop` — ветка разработки
- Ветки: `feature/`, `fix/`, `exp/`

## Документация

- [`docs/decisions/`](docs/decisions/) — ADR и Q&A с заказчиком
- [`docs/api/interfaces.md`](docs/api/interfaces.md) — контракты модулей
- [`CLAUDE.md`](CLAUDE.md) — контекст для AI-агентов
