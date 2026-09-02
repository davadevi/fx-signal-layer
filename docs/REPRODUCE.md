# Воспроизведение результатов

Инструкция для постороннего человека повторить все результаты с нуля.

## Требования

- Python 3.11+
- Git
- Интернет (для загрузки данных ЦБ РФ)

## Установка

```bash
git clone https://github.com/davadevi/fx-signal-layer.git
cd fx-signal-layer

pip install uv
uv sync --extra dev
pre-commit install
```

## Данные

Источник: [ЦБ РФ — официальные курсы валют](https://www.cbr.ru/development/SXML/)  
Открытый XML API, бесплатно, без регистрации.

```bash
make data
# Скачивает курсы за 2019–2026 по коридорам RUB/TJS/UZS/KGS/AMD/KZT + USD/EUR/CNY
# Нормализует номиналы, применяет forward-fill для выходных
# Результат: data/processed/rates.parquet
```

## Запуск бэктеста

```bash
make backtest
# Walk-forward по всем индикаторам × 5 коридоров
# Результат: reports/*.json + reports/summary.html
```

## Сигналы на произвольную дату

```bash
make signals DATE=2025-06-15
# Или:
python -m src.pipeline.run --cutoff-date 2025-06-15
```

Вывод: таблица `[date, corridor, indicator, direction, strength, push_text]`

## Проверка no-lookahead

```bash
make test
# Включает тест test_no_lookahead.py — проверяет что compute() не использует данные после cutoff_date
```

## Ожидаемый вывод

После `make backtest`:
- `reports/summary.html` — матрица индикатор × коридор × метрики
- Lift ≥ 1.3 на коридорах RUB_TJS, RUB_UZS на периоде 2023–2026
- Частота: 1–2 сигнала/коридор/неделю

## Примечания

- Все данные публичные и воспроизводимые
- Никаких API-ключей не требуется
- 2022 год исключён из обучения ML-моделей (задокументировано в ADR-003)
- Курс ЦБ ≠ курс исполнения в приложении (зафиксировано как допущение)
