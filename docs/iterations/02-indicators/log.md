# Log: Indicators
<!-- Newest first. -->

## 2026-09-03 — Baseline indicator set implemented

Modules added under `src/indicators/`:

- `percentile.py` — `PercentileRankIndicator(window=30, threshold=0.20)`. Score in [0,1] = fraction of prior trading days in window with lower rate. Signal fires when score < threshold. Primary indicator.
- `rsi.py` — `RSIFilter(period=14, threshold=35)`. Wilder EWM RSI on trading days only, score = RSI/100. Signal when score <= 0.35. Overrides `get_signal` (fires on low, not high).
- `volatility_regime.py` — `VolatilityRegimeFilter(vol_window=30, pct_window=252, crisis_pct=0.85)`. Binary score: 1 = calm (allow signals), 0 = crisis (suppress). Uses annualized realized vol vs its own 1y rolling 85th percentile.
- `momentum.py` — `MomentumIndicator(lookback_days=5)`. Rolling percentile rank of 5-day pct change. Included as expected-negative baseline (trend continuation hypothesis).

Design points:
- Every `compute()` starts with `self._filter(df, corridor, cutoff_date)` — no lookahead by construction.
- All indicators filter to `is_trading_day == True` before computing, then reindex to full calendar and ffill so downstream code can query weekend/holiday dates.
- `_filter` in `BaseIndicator` was patched to coerce `cutoff_date` to `pd.Timestamp` (parquet stores datetime64, base compared with `datetime.date` and raised).

Tests: `tests/unit/test_indicators.py` covers no-lookahead per indicator, score ranges, and directional semantics (percentile fires on downtrend, doesn't fire on uptrend, RSI fires on downtrend, regime detects synthetic crisis). All 25 tests pass.

## 2026-09-03 — Pipeline output on 2024-06-15 (sanity)

```
RUB_KZT  favorable_now  strength=0.966  pct=0.034  calm
RUB_KGS  favorable_now  strength=0.897  pct=0.103  calm
```
