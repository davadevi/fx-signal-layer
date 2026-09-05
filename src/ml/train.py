"""LightGBM walk-forward training with asymmetric error weighting.

Purged, embargoed quarterly walk-forward identical to src/backtest/engine.py:
- TRAIN_START = 2022-04-01
- train_years=2 years, test_months=3 months, embargo_days=5
- Windows shift forward quarterly.

Asymmetric loss: false positives (predicting "good day", rate actually fell)
cost FP_WEIGHT times more than false negatives. Implemented via sample weights
on the negative class during training.

Threshold: probability threshold p* chosen from training-fold predictions
such that ~1 signal per 5 trading days fires (~1/week). Applied unchanged to
test fold — no test data used for threshold selection.

Regime suppression: if regime feature == 0.0 (crisis) on a test day, the
signal is suppressed regardless of the model's probability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta

from src.backtest.metrics import (
    base_rate_at_h,
    clustering_score,
    hit_rate_at_h,
    lift_over_random,
)
from src.ml.features import FEATURE_COLUMNS, build_features
from src.ml.labels import make_labels


TRAIN_START = date(2022, 4, 1)
OOT_START = date(2025, 7, 1)
H_HORIZONS = [1, 3, 5, 10, 20]
FP_WEIGHT = 3.0
TARGET_SIGNAL_RATE = 1.0 / 3.0  # ~1 signal per 3 trading days (~1.5/wk)
MANDATORY_SIGNAL_RATE = 1.0 / 10.0  # top ~10% of probs = mandatory
OPTIONAL_SIGNAL_RATE = 1.0 / 3.0  # top ~33% of probs = optional (includes mandatory)

LGB_PARAMS: dict[str, Any] = {
    "objective": "binary",
    "metric": "binary_logloss",
    "n_estimators": 200,
    "learning_rate": 0.05,
    "num_leaves": 15,
    "min_child_samples": 5,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
    "random_state": 42,
}


@dataclass
class MLResult:
    corridor: str
    lift_A: dict[int, float]
    lift_A_oot: dict[int, float]
    signal_count: int
    signals_per_week: float
    feature_importance: dict[str, float]
    threshold: float
    hit_rate: dict[int, float]
    base_rate: dict[int, float]
    n_windows: int
    clustering_score: float
    mandatory_count: int = 0
    optional_count: int = 0
    mandatory_lift: dict[int, float] = None  # type: ignore[assignment]
    optional_lift: dict[int, float] = None  # type: ignore[assignment]
    threshold_mandatory: float = float("nan")
    threshold_optional: float = float("nan")

    def to_json(self) -> dict:
        def _d(x: dict[int, float] | None) -> dict[str, float]:
            if x is None:
                return {}
            return {str(k): v for k, v in x.items()}

        return {
            "corridor": self.corridor,
            "lift_A": _d(self.lift_A),
            "lift_A_oot": _d(self.lift_A_oot),
            "signal_count": self.signal_count,
            "signals_per_week": self.signals_per_week,
            "feature_importance": self.feature_importance,
            "threshold": self.threshold,
            "hit_rate": _d(self.hit_rate),
            "base_rate": _d(self.base_rate),
            "n_windows": self.n_windows,
            "clustering_score": self.clustering_score,
            "mandatory_count": self.mandatory_count,
            "optional_count": self.optional_count,
            "mandatory_lift": _d(self.mandatory_lift),
            "optional_lift": _d(self.optional_lift),
            "threshold_mandatory": self.threshold_mandatory,
            "threshold_optional": self.threshold_optional,
        }


def _build_full_rate_series(df: pd.DataFrame, corridor: str) -> pd.Series:
    sub = df[df["corridor"] == corridor].sort_values("date")
    if sub.empty:
        return pd.Series(dtype=float)
    s = sub.set_index("date")["rate"]
    full_idx = pd.date_range(sub["date"].min(), sub["date"].max(), freq="D")
    return s.reindex(full_idx).ffill()


def _pick_threshold(train_probs: np.ndarray, target_rate: float) -> float:
    """Quantile threshold so that fraction of train days above threshold == target_rate."""
    if len(train_probs) == 0:
        return 0.5
    q = 1.0 - target_rate
    q = min(max(q, 0.0), 1.0)
    return float(np.quantile(train_probs, q))


def _pick_two_thresholds(
    train_probs: np.ndarray,
    mandatory_rate: float,
    optional_rate: float,
) -> tuple[float, float]:
    """Returns (threshold_mandatory, threshold_optional) from training probs.

    Guarantees t_optional < t_mandatory so the two zones don't overlap.
    """
    if len(train_probs) == 0:
        return 0.5, 0.4
    q_mandatory = 1 - mandatory_rate
    q_optional = 1 - optional_rate
    t_mand = float(np.quantile(train_probs, q_mandatory))
    t_opt = float(np.quantile(train_probs, q_optional))
    if t_opt >= t_mand:
        t_opt = t_mand * 0.95  # ensure strict ordering
    return t_mand, t_opt


def run_ml_walkforward(
    corridor: str,
    df: pd.DataFrame,
    h: int = 5,
    train_years: int = 2,
    test_months: int = 3,
    embargo_days: int = 5,
    fp_weight: float = FP_WEIGHT,
    cooldown_days: int = 3,
    save_report: bool = True,
    reports_dir: str = "reports",
) -> MLResult:
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])

    corridor_df = df[df["corridor"] == corridor].copy()
    if corridor_df.empty:
        raise ValueError(f"No data for corridor {corridor}")

    rates_full = _build_full_rate_series(df, corridor)
    labels_full = make_labels(df, corridor, h=h)

    data_end = corridor_df["date"].max().date()
    max_h = max(H_HORIZONS)
    last_test_end = data_end - timedelta(days=max_h)

    all_signals: list[date] = []
    all_trading_days: list[pd.Timestamp] = []
    oot_signals: list[date] = []
    oot_trading_days: list[pd.Timestamp] = []
    thresholds: list[float] = []
    thresholds_mand: list[float] = []
    thresholds_opt: list[float] = []
    mandatory_signals_all: list[date] = []
    optional_signals_all: list[date] = []
    importances: list[np.ndarray] = []
    n_windows = 0

    test_start = TRAIN_START + relativedelta(years=train_years)
    while test_start <= last_test_end:
        test_end = min(
            test_start + relativedelta(months=test_months) - timedelta(days=1),
            last_test_end,
        )
        train_start = test_start - relativedelta(years=train_years)
        train_end = test_start - timedelta(days=1)

        # Build features with cutoff = train_end for training (strict no lookahead)
        train_feats = build_features(df, corridor, train_end)
        train_labels = labels_full.reindex(train_feats.index)

        # Exclude last h days: their labels require rate[t+h] from the test window (lookahead).
        label_cutoff = train_end - timedelta(days=h)
        train_mask = (
            (train_feats.index >= pd.Timestamp(train_start))
            & (train_feats.index <= pd.Timestamp(label_cutoff))
            & train_labels.notna()
            & train_feats.notna().all(axis=1)
        )
        X_train = train_feats.loc[train_mask]
        y_train = train_labels.loc[train_mask].astype(int)

        if len(X_train) < 50 or y_train.nunique() < 2:
            test_start = test_start + relativedelta(months=test_months)
            continue

        # Asymmetric sample weights: FP costs more → weight negatives (label=0) higher.
        sample_weight = np.where(y_train.values == 1, 1.0, fp_weight)

        model = lgb.LGBMClassifier(**LGB_PARAMS)
        model.fit(X_train.values, y_train.values, sample_weight=sample_weight)

        train_probs = model.predict_proba(X_train.values)[:, 1]
        threshold = _pick_threshold(train_probs, TARGET_SIGNAL_RATE)
        t_mand, t_opt = _pick_two_thresholds(
            train_probs, MANDATORY_SIGNAL_RATE, OPTIONAL_SIGNAL_RATE
        )
        thresholds.append(threshold)
        thresholds_mand.append(t_mand)
        thresholds_opt.append(t_opt)
        importances.append(model.feature_importances_.astype(float))

        # Test fold: features with cutoff = test_end (no post-test data leaked)
        test_feats = build_features(df, corridor, test_end)
        effective_test_start = test_start + timedelta(days=embargo_days)
        test_window_mask = (
            (test_feats.index >= pd.Timestamp(effective_test_start))
            & (test_feats.index <= pd.Timestamp(test_end))
        )
        test_feats_window = test_feats.loc[test_window_mask]

        # Any row with all-NaN features cannot be scored
        valid_mask = test_feats_window.notna().all(axis=1)
        if valid_mask.sum() == 0:
            all_trading_days.extend(list(test_feats_window.index))
            if test_start >= OOT_START:
                oot_trading_days.extend(list(test_feats_window.index))
            n_windows += 1
            test_start = test_start + relativedelta(months=test_months)
            continue

        X_test = test_feats_window.loc[valid_mask]
        test_probs = model.predict_proba(X_test.values)[:, 1]

        # Regime suppression: crisis days (regime==0.0) get their signal killed.
        regime_vals = X_test["regime"].values
        alive = regime_vals > 0.0

        mandatory_mask = (test_probs >= t_mand) & alive
        optional_mask = (test_probs >= t_opt) & (test_probs < t_mand) & alive

        raw_mandatory = [ts.date() for ts, m in zip(X_test.index, mandatory_mask) if m]
        raw_optional = [ts.date() for ts, m in zip(X_test.index, optional_mask) if m]

        # Mandatory: no cooldown.
        fold_mandatory = sorted(raw_mandatory)

        # Optional: cooldown against mandatory (this fold + all history so far)
        # + previously kept optional. Iterate in chronological order.
        prior_dates = sorted(set(mandatory_signals_all + optional_signals_all + fold_mandatory))
        fold_optional: list[date] = []
        for d in sorted(raw_optional):
            all_prior = prior_dates + fold_optional
            if all_prior:
                too_close = any(abs((d - p).days) < cooldown_days for p in all_prior)
                if too_close:
                    continue
            fold_optional.append(d)

        mandatory_signals_all.extend(fold_mandatory)
        optional_signals_all.extend(fold_optional)

        cd_signals = sorted(fold_mandatory + fold_optional)
        all_signals.extend(cd_signals)
        all_trading_days.extend(list(test_feats_window.index))
        if test_start >= OOT_START:
            oot_signals.extend(cd_signals)
            oot_trading_days.extend(list(test_feats_window.index))

        n_windows += 1
        test_start = test_start + relativedelta(months=test_months)

    trading_idx = pd.DatetimeIndex(all_trading_days)
    oot_idx = pd.DatetimeIndex(oot_trading_days)

    hit_rate = {hh: hit_rate_at_h(all_signals, rates_full, hh) for hh in H_HORIZONS}
    base_rate = {hh: base_rate_at_h(trading_idx, rates_full, hh) for hh in H_HORIZONS}
    lift_A = {hh: lift_over_random(all_signals, rates_full, trading_idx, hh) for hh in H_HORIZONS}
    lift_A_oot = {hh: lift_over_random(oot_signals, rates_full, oot_idx, hh) for hh in H_HORIZONS}
    mandatory_lift = {
        hh: lift_over_random(mandatory_signals_all, rates_full, trading_idx, hh)
        for hh in H_HORIZONS
    }
    optional_lift = {
        hh: lift_over_random(optional_signals_all, rates_full, trading_idx, hh)
        for hh in H_HORIZONS
    }

    if all_trading_days:
        span_days = (max(all_trading_days) - min(all_trading_days)).days + 1
        weeks = max(span_days / 7.0, 1e-9)
        signals_per_week = len(all_signals) / weeks
    else:
        signals_per_week = 0.0

    if importances:
        avg_imp = np.mean(np.vstack(importances), axis=0)
        total = avg_imp.sum()
        if total > 0:
            avg_imp = avg_imp / total
        feature_importance = dict(zip(FEATURE_COLUMNS, avg_imp.tolist()))
    else:
        feature_importance = {c: 0.0 for c in FEATURE_COLUMNS}

    result = MLResult(
        corridor=corridor,
        lift_A=lift_A,
        lift_A_oot=lift_A_oot,
        signal_count=len(all_signals),
        signals_per_week=signals_per_week,
        feature_importance=feature_importance,
        threshold=float(np.mean(thresholds)) if thresholds else float("nan"),
        hit_rate=hit_rate,
        base_rate=base_rate,
        n_windows=n_windows,
        clustering_score=clustering_score(all_signals),
        mandatory_count=len(mandatory_signals_all),
        optional_count=len(optional_signals_all),
        mandatory_lift=mandatory_lift,
        optional_lift=optional_lift,
        threshold_mandatory=float(np.mean(thresholds_mand)) if thresholds_mand else float("nan"),
        threshold_optional=float(np.mean(thresholds_opt)) if thresholds_opt else float("nan"),
    )

    if save_report:
        import json

        out_dir = Path(reports_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = date.today().isoformat()
        out_path = out_dir / f"ml_lgbm_{corridor}_{stamp}.json"
        out_path.write_text(json.dumps(result.to_json(), indent=2, ensure_ascii=False))

    return result
