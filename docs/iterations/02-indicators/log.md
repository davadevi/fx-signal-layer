# Log: Indicators
<!-- Newest first. -->

## 2026-09-03 — LogReturnPercentileIndicator added (fixes lift<1 on non-stationary series)

Problem: `PercentileRankIndicator` (30-day absolute-level rank) gave lift 0.86–0.97 across all five corridors. Diagnosis: RUB/CIS rates are I(1) (ADF p=0.32–0.61), so applying an I(0) oscillator to a trending series mathematically guarantees lift<1 in the trending regime — "lowest of the last 30 days" during a persistent downtrend is not evidence of a local minimum.

Fix: new module `src/indicators/log_return_percentile.py` — `LogReturnPercentileIndicator(return_window=5, rank_window=60, threshold=0.20, confirm_days=K)`. Ranks the 5-day log-return in a 60-day rolling window. Log-returns of I(1) series are I(0), so the rank statistic is well defined regardless of trend. Optional `confirm_days` filter requires K consecutive rising trading days (reversal already visible) before allowing the signal.

Score in [0, 1], signal fires when score < threshold. Same interface as other indicators (`_filter` first, filter to `is_trading_day`, ffill to full calendar).

Backtest across all five corridors (walk-forward, cooldown=3d, embargo=5d, `train_years=2`, `test_months=3`):

| Indicator                     | corridor   | lift_A@5 | lift_B@5 | CI_low@5 | CI_high@5 | n_sig | sig/wk |
|-------------------------------|------------|----------|----------|----------|-----------|-------|--------|
| percentile_30d (baseline)     | RUB_TJS    |    0.939 |    0.854 |    0.730 |     1.174 |    72 |   0.58 |
| percentile_30d                | RUB_UZS    |    0.862 |    0.821 |    0.646 |     1.077 |    83 |   0.67 |
| percentile_30d                | RUB_KGS    |    0.912 |    0.852 |    0.706 |     1.117 |    86 |   0.70 |
| percentile_30d                | RUB_AMD    |    0.958 |    0.912 |    0.753 |     1.163 |    88 |   0.71 |
| percentile_30d                | RUB_KZT    |    0.966 |    0.972 |    0.781 |     1.171 |    98 |   0.79 |
| log_ret_5d_60w                | RUB_TJS    |    1.096 |    0.929 |    0.845 |     1.346 |    60 |   0.49 |
| log_ret_5d_60w                | RUB_UZS    |    1.041 |    0.958 |    0.788 |     1.293 |    63 |   0.51 |
| log_ret_5d_60w                | RUB_KGS    |    0.997 |    0.862 |    0.764 |     1.229 |    59 |   0.48 |
| log_ret_5d_60w                | RUB_AMD    |    1.003 |    0.842 |    0.744 |     1.262 |    62 |   0.50 |
| log_ret_5d_60w                | RUB_KZT    |    1.084 |    1.061 |    0.836 |     1.332 |    65 |   0.53 |
| log_ret_5d_60w_confirm2       | RUB_TJS    |    1.476 |    1.510 |    1.073 |     1.878 |    14 |   0.11 |
| log_ret_5d_60w_confirm2       | RUB_UZS    |    1.222 |    1.198 |    0.760 |     1.681 |    13 |   0.11 |
| log_ret_5d_60w_confirm2       | RUB_KGS    |    1.604 |    1.665 |    1.069 |     1.960 |    11 |   0.09 |
| log_ret_5d_60w_confirm2       | RUB_AMD    |    1.405 |    1.405 |    0.803 |     2.007 |    10 |   0.08 |
| log_ret_5d_60w_confirm2       | RUB_KZT    |    1.007 |    1.014 |    0.503 |     1.678 |    12 |   0.10 |

Findings:
- Log-return rank without reversal confirmation moves lift to ~1.0–1.1 (parity with random) — mathematical bug is fixed but no edge yet.
- Adding `confirm_days=2` yields lift 1.0–1.6 on 4 of 5 corridors, with 95% bootstrap CI strictly above 1.0 on RUB_TJS and RUB_KGS. RUB_KZT variant is not distinguishable from random (CI [0.50, 1.68]).
- Signal frequency drops to 0.08–0.11 per week — well within the 1–2/wk cap; deployment likely needs a lower `confirm_days` (1) or an OR with a second indicator to hit the target rate.
- Selected `log_ret_5d_60w_confirm2` as primary in `src/pipeline/signals.py`.

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
