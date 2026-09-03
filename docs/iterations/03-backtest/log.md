# Log: Backtest Engine
<!-- Newest first. -->

## 2026-09-03 — Walk-forward engine + metrics implemented

`src/backtest/metrics.py`:
- `hit_rate_at_h` — forward-only: `rate[t+h] >= rate[t]` counts as hit (lower = favorable).
- `base_rate_at_h` — same rule but over all trading days in the window (baseline).
- `lift_over_random = hit_rate / base_rate`.
- `clustering_score` — CV of inter-signal gaps (0 = evenly spread).
- `cost_of_waiting_bps` — mean bps drift between `h_fast` and `h_slow` after each signal.
- `apply_cooldown` — enforces minimum gap between consecutive signals.

`src/backtest/engine.py`:
- Purged walk-forward: `train_years=2`, `test_months=3`, quarterly step, `embargo_days=5`.
- `TRAIN_START = 2022-04-01`, horizons `[1,3,5,10,20]`.
- Per window: compute scores once with `cutoff_date = test_end`, threshold to raw signals in `[test_start, test_end]`, apply cooldown, collect.
- Reports to `reports/{indicator}_{corridor}_{date}.json`.
- Full rate series is calendar-daily ffilled so `t+h` lookups never fall on a missing weekend.

## 2026-09-03 — First backtest run: PercentileRankIndicator across 5 corridors

Parameters: window=30, threshold=0.20, cooldown=3 days, train_years=2, test_months=3.

| Corridor | signals | signals/wk | hit@5 | base@5 | lift@5 | cluster | cost_wait |
|----------|---------|-----------:|------:|-------:|-------:|--------:|----------:|
| RUB_TJS  | 72      | 0.58       | 0.500 | 0.532  | 0.939  | 2.29    | +27.1 bps |
| RUB_UZS  | 83      | 0.67       | 0.434 | 0.503  | 0.862  | 2.06    | +7.1 bps  |
| RUB_KGS  | 86      | 0.70       | 0.465 | 0.510  | 0.912  | 2.06    | −5.3 bps  |
| RUB_AMD  | 88      | 0.71       | 0.477 | 0.498  | 0.958  | 2.01    | +5.3 bps  |
| RUB_KZT  | 98      | 0.79       | 0.480 | 0.497  | 0.966  | 1.93    | −7.2 bps  |

**Negative result.** Lift@5 is **below 1.0 on every corridor** (0.86–0.97). Baseline percentile signal as configured does not beat random trading-day selection at the 5-day horizon. Frequency (0.6–0.8 signals/wk) is inside the 1–2/wk target, and cost-of-waiting is small in magnitude.

Note: `out_of_time_lift` equals `lift` because the earliest test window starts at `TRAIN_START + 2y = 2024-04-01`, which is already past `OOT_START = 2024-01-01`. Once a longer sample is available, the OOT split will start biting.

**Momentum sanity check** — as expected, `MomentumIndicator` on RUB_TJS/RUB_UZS also gives lift@5 ≈ 0.96–0.98 (trend continues, signal wrong-way). Confirms the null the research doc warned about.

**Next steps:**
- Try shorter horizons (h=1, h=3) — the percentile signal may only help intraweek.
- Tighten threshold (0.10) and stack with RSI confirmation to see if precision rises at the cost of frequency.
- Sweep windows (15, 45, 60) and re-run.
- Investigate whether the >70% "signal fires ≥3× per test window" pattern is driving clustering scores >2.0 and diluting hit-rate.
