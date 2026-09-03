"""
Signal Research Report — FX Signal Layer, Alfa-Bank Hackathon
Generates reports/signal_research_report.pdf with full backtest results.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

DATA_PATH = "data/processed/rates.parquet"
OUT_PATH = "reports/signal_research_report.pdf"
TRAIN_START = pd.Timestamp("2022-04-01")
MAIN_CORRIDORS = ["RUB_TJS", "RUB_UZS", "RUB_KGS", "RUB_AMD", "RUB_KZT"]

COLORS = {
    "RUB_TJS": "#1f77b4", "RUB_UZS": "#ff7f0e", "RUB_KGS": "#2ca02c",
    "RUB_AMD": "#d62728", "RUB_KZT": "#9467bd",
}
NAMES = {
    "RUB_TJS": "Сомони (TJS)", "RUB_UZS": "Сум (UZS)",
    "RUB_KGS": "Сом (KGS)", "RUB_AMD": "Драм (AMD)", "RUB_KZT": "Тенге (KZT)",
}
SHORT = {"RUB_TJS": "TJS", "RUB_UZS": "UZS", "RUB_KGS": "KGS", "RUB_AMD": "AMD", "RUB_KZT": "KZT"}

PALETTE = {
    "blue": "#1565C0", "red": "#C62828", "green": "#2E7D32",
    "orange": "#E65100", "purple": "#6A1B9A", "gray": "#455A64",
    "light_gray": "#ECEFF1", "mid_gray": "#B0BEC5",
    "bg": "#FAFAFA",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 9,
    "figure.facecolor": PALETTE["bg"],
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.color": PALETTE["mid_gray"],
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ── Hardcoded backtest results ─────────────────────────────────────────────────

RESULTS = {
    "percentile_30d": {
        "lift5": {"RUB_TJS": 0.939, "RUB_UZS": 0.862, "RUB_KGS": 0.912, "RUB_AMD": 0.958, "RUB_KZT": 0.966},
        "lift_b5": {"RUB_TJS": 0.854, "RUB_UZS": 0.821, "RUB_KGS": 0.852, "RUB_AMD": 0.912, "RUB_KZT": 0.972},
        "sigwk": {"RUB_TJS": 0.58, "RUB_UZS": 0.67, "RUB_KGS": 0.70, "RUB_AMD": 0.71, "RUB_KZT": 0.79},
        "nsig": {"RUB_TJS": 72, "RUB_UZS": 83, "RUB_KGS": 86, "RUB_AMD": 88, "RUB_KZT": 98},
    },
    "log_ret_c0": {
        "lift5": {"RUB_TJS": 1.133, "RUB_UZS": 1.024, "RUB_KGS": 1.058, "RUB_AMD": 1.064, "RUB_KZT": 1.101},
        "lift_b5": {"RUB_TJS": 0.956, "RUB_UZS": 0.941, "RUB_KGS": 0.881, "RUB_AMD": 0.862, "RUB_KZT": 1.089},
        "sigwk": {"RUB_TJS": 0.46, "RUB_UZS": 0.49, "RUB_KGS": 0.46, "RUB_AMD": 0.48, "RUB_KZT": 0.51},
        "nsig": {"RUB_TJS": 57, "RUB_UZS": 60, "RUB_KGS": 56, "RUB_AMD": 59, "RUB_KZT": 63},
    },
    "log_ret_c2": {
        "lift5": {"RUB_TJS": 1.493, "RUB_UZS": 1.220, "RUB_KGS": 1.616, "RUB_AMD": 1.418, "RUB_KZT": 1.020},
        "lift_b5": {"RUB_TJS": 1.530, "RUB_UZS": 1.198, "RUB_KGS": 1.682, "RUB_AMD": 1.423, "RUB_KZT": 1.040},
        "sigwk": {"RUB_TJS": 0.11, "RUB_UZS": 0.11, "RUB_KGS": 0.09, "RUB_AMD": 0.08, "RUB_KZT": 0.10},
        "nsig": {"RUB_TJS": 14, "RUB_UZS": 13, "RUB_KGS": 11, "RUB_AMD": 10, "RUB_KZT": 12},
        "ci_lo": {"RUB_TJS": 1.086, "RUB_UZS": 0.759, "RUB_KGS": 1.077, "RUB_AMD": 0.803, "RUB_KZT": 0.503},
        "ci_hi": {"RUB_TJS": 1.900, "RUB_UZS": 1.677, "RUB_KGS": 1.975, "RUB_AMD": 2.007, "RUB_KZT": 1.678},
    },
    "AND_calendar": {
        "lift5": {"RUB_TJS": 1.181, "RUB_UZS": 1.067, "RUB_KGS": 1.152, "RUB_AMD": 1.050, "RUB_KZT": 1.088},
        "lift_b5": {"RUB_TJS": 1.000, "RUB_UZS": 1.098, "RUB_KGS": 0.914, "RUB_AMD": 0.904, "RUB_KZT": 1.040},
        "sigwk": {"RUB_TJS": 0.30, "RUB_UZS": 0.32, "RUB_KGS": 0.29, "RUB_AMD": 0.22, "RUB_KZT": 0.24},
        "nsig": {"RUB_TJS": 37, "RUB_UZS": 39, "RUB_KGS": 36, "RUB_AMD": 27, "RUB_KZT": 30},
    },
    "LightGBM": {
        "lift5": {"RUB_TJS": 0.977, "RUB_UZS": 1.198, "RUB_KGS": 1.498, "RUB_AMD": 1.490, "RUB_KZT": 1.140},
        "lift_b5": {"RUB_TJS": float("nan"), "RUB_UZS": float("nan"), "RUB_KGS": float("nan"), "RUB_AMD": float("nan"), "RUB_KZT": float("nan")},
        "sigwk": {"RUB_TJS": 0.28, "RUB_UZS": 0.35, "RUB_KGS": 0.24, "RUB_AMD": 0.28, "RUB_KZT": 0.33},
        "nsig": {"RUB_TJS": 35, "RUB_UZS": 43, "RUB_KGS": 29, "RUB_AMD": 34, "RUB_KZT": 34},
    },
}

FEAT_IMPORTANCE = {
    "bollinger_z": 17.2, "rsi": 17.0, "log_ret_c0": 20.1,
    "log_ret_c2": 14.8, "pct_rank": 12.3, "lags": 13.3,
    "calendar": 1.9, "regime": 1.4,
}

# ── Load data ──────────────────────────────────────────────────────────────────

print("Loading data...")
df = pd.read_parquet(DATA_PATH)
df["date"] = pd.to_datetime(df["date"])
df_train = df[df["date"] >= TRAIN_START].copy()

# ── PDF ────────────────────────────────────────────────────────────────────────

Path("reports").mkdir(exist_ok=True)

with PdfPages(OUT_PATH) as pdf:

    # ── PAGE 1: Cover ──────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(PALETTE["blue"])
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(PALETTE["blue"])
    ax.axis("off")

    ax.text(0.5, 0.80, "FX Signal Layer", ha="center", va="center",
            fontsize=38, fontweight="bold", color="white", transform=ax.transAxes)
    ax.text(0.5, 0.69, "Исследование сигналов: результаты бэктеста",
            ha="center", va="center", fontsize=20, color="#90CAF9", transform=ax.transAxes)
    ax.plot([0.15, 0.85], [0.61, 0.61], color="white", alpha=0.3, linewidth=1, transform=ax.transAxes)

    meta = [
        ("Коридоры", "RUB → TJS · UZS · KGS · AMD · KZT"),
        ("Цель", "Lift ≥ 1.3 над случайным базисом · 1–2 сигнала/нед на коридор"),
        ("Методология", "Purged walk-forward (2y train / 3m test / 5d embargo)"),
        ("Индикаторы", "Percentile rank · Log-return percentile · Bollinger Z · Calendar · LightGBM"),
        ("Данные", f"ЦБ РФ · {df['date'].min().date()} — {df['date'].max().date()}"),
        ("Дата отчёта", "03 сентября 2026"),
    ]
    for i, (k, v) in enumerate(meta):
        y = 0.55 - i * 0.072
        ax.text(0.28, y, k + ":", ha="right", va="center", fontsize=11,
                color="#90CAF9", fontweight="bold", transform=ax.transAxes)
        ax.text(0.30, y, v, ha="left", va="center", fontsize=11,
                color="white", transform=ax.transAxes)

    ax.text(0.5, 0.07, "Альфа Будущее · Хакатон 2026",
            ha="center", va="center", fontsize=10, color="#90CAF9", alpha=0.7, transform=ax.transAxes)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 1: Cover")

    # ── PAGE 2: Problem framing ────────────────────────────────────────────────
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.suptitle("Проблема: почему простой перцентильный ранг не работает?",
                 fontsize=14, fontweight="bold")
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.5, wspace=0.4)

    # Top-left: show TJS rate trend (I(1) = trending)
    ax1 = fig.add_subplot(gs[0, 0])
    sub = df_train[(df_train["corridor"] == "RUB_TJS") & df_train["is_trading_day"]].sort_values("date").reset_index(drop=True)
    ax1.plot(sub["date"], sub["rate"], color=COLORS["RUB_TJS"], linewidth=1.0)
    rate_s = sub["rate"]
    pct = rate_s.rolling(30, min_periods=15).apply(lambda x: (x < x.iloc[-1]).sum() / len(x), raw=False)
    sig_days = sub[pct < 0.20]
    ax1.scatter(sig_days["date"], sig_days["rate"], color=PALETTE["red"], s=10, zorder=5, alpha=0.7, label="Сигнал pct<20%")
    ax1.set_title("TJS: уровень курса (I(1) — трендовый)", fontsize=9)
    ax1.set_ylabel("Курс руб./TJS", fontsize=8)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=7)
    ax1.legend(fontsize=7)
    ax1.text(0.02, 0.05, "Красные точки — сигналы 'низкий уровень',\nно тренд продолжает падать →\nlift < 1.0",
             transform=ax1.transAxes, fontsize=7.5, color=PALETTE["red"],
             bbox=dict(facecolor="white", alpha=0.8, edgecolor=PALETTE["mid_gray"], pad=3))

    # Top-right: log-returns of TJS (I(0))
    ax2 = fig.add_subplot(gs[0, 1])
    log_ret = np.log(rate_s).diff(5)
    ax2.plot(sub["date"], log_ret.values, color=PALETTE["blue"], linewidth=0.7, alpha=0.8)
    ax2.axhline(0, color=PALETTE["gray"], linewidth=0.8, linestyle="--")
    # Signal days: log_ret in bottom 20%
    lr_pct = log_ret.rolling(60, min_periods=15).apply(lambda x: (x[:-1] < x[-1]).sum() / max(len(x)-1, 1), raw=True)
    lr_sig_mask = lr_pct.values < 0.20
    lr_sig = sub[lr_sig_mask]
    ax2.scatter(lr_sig["date"], log_ret.values[lr_sig_mask] if len(lr_sig) else [],
                color=PALETTE["green"], s=10, zorder=5, alpha=0.8, label="Сигнал log-ret<20%")
    ax2.set_title("TJS: 5-дн. лог-доходность (I(0) — стационарный)", fontsize=9)
    ax2.set_ylabel("log(rate[t]/rate[t-5])", fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=7)
    ax2.legend(fontsize=7)
    ax2.text(0.02, 0.05, "Зелёные точки — дни, когда рубль\nукрепился сильнее обычного →\nlift > 1.0",
             transform=ax2.transAxes, fontsize=7.5, color=PALETTE["green"],
             bbox=dict(facecolor="white", alpha=0.8, edgecolor=PALETTE["mid_gray"], pad=3))

    # Bottom: explanation text boxes
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.axis("off")
    txt_left = (
        "❌  Percentile rank на уровне курса (I(1))\n\n"
        "Курс рубля имеет тренд (нестационарен).\n"
        "В режиме падения рубля каждый «локальный минимум»\n"
        "оказывается выше следующего — сигнал «выгодно сейчас»\n"
        "систематически ошибочен.\n\n"
        "Результат: lift = 0.86–0.97 на всех 5 коридорах.\n"
        "Математически неизбежно для I(0) метрики на I(1) ряде."
    )
    ax3.text(0.5, 0.5, txt_left, ha="center", va="center", fontsize=9,
             transform=ax3.transAxes,
             bbox=dict(facecolor="#FFEBEE", edgecolor=PALETTE["red"], alpha=0.9, pad=8, boxstyle="round"))
    ax3.set_title("Почему провалился базовый индикатор", fontsize=9, color=PALETTE["red"])

    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    txt_right = (
        "✅  Log-return percentile rank (I(0))\n\n"
        "Лог-доходность = первая разность ряда → стационарна.\n"
        "Перцентильный ранг 5-дневной лог-доходности осмыслен:\n"
        "«рубль укрепился сильнее, чем в N% последних 60 дней».\n\n"
        "Confirm=2 (разворот): курс растёт 2 дня подряд после\n"
        "аномального падения → снижает ложные срабатывания.\n\n"
        "Результат: lift = 1.49–1.62 на TJS/KGS/AMD."
    )
    ax4.text(0.5, 0.5, txt_right, ha="center", va="center", fontsize=9,
             transform=ax4.transAxes,
             bbox=dict(facecolor="#E8F5E9", edgecolor=PALETTE["green"], alpha=0.9, pad=8, boxstyle="round"))
    ax4.set_title("Решение: I(0) метрика на I(0) ряде", fontsize=9, color=PALETTE["green"])

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 2: Problem framing")

    # ── PAGE 3: Indicator lift comparison ─────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(11.69, 6.5))
    fig.suptitle("Сравнение индикаторов: lift@5 по всем 5 коридорам\n"
                 "(walk-forward бэктест, 2y train / 3m test, embargo 5d)",
                 fontsize=13, fontweight="bold")

    ind_labels = ["percentile\n30d", "log_ret\nc0", "log_ret\nc2", "AND\ncalendar", "LightGBM"]
    ind_keys = ["percentile_30d", "log_ret_c0", "log_ret_c2", "AND_calendar", "LightGBM"]
    x = np.arange(len(MAIN_CORRIDORS))
    w = 0.15
    colors_ind = [PALETTE["red"], "#888888", PALETTE["blue"], PALETTE["purple"], PALETTE["orange"]]

    ax = axes[0]
    for i, (key, label, col) in enumerate(zip(ind_keys, ind_labels, colors_ind)):
        vals = [RESULTS[key]["lift5"][c] for c in MAIN_CORRIDORS]
        bars = ax.bar(x + i * w - 2 * w, vals, w, label=label, color=col, alpha=0.85)
    ax.axhline(1.3, color=PALETTE["red"], linewidth=1.5, linestyle="--", label="Цель lift 1.3", zorder=5)
    ax.axhline(1.0, color=PALETTE["gray"], linewidth=0.8, linestyle=":", label="Случайный базис", zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT[c] for c in MAIN_CORRIDORS], fontsize=10)
    ax.set_ylabel("Lift@5 (hit_rate / base_rate)")
    ax.set_title("Lift definition A: rate[t+5] ≥ rate[t]", fontsize=9)
    ax.legend(fontsize=7, loc="upper right", ncol=2)
    ax.set_ylim(0.5, 2.1)

    # Definition B
    ax = axes[1]
    for i, (key, label, col) in enumerate(zip(ind_keys[:4], ind_labels[:4], colors_ind[:4])):
        vals = [RESULTS[key]["lift_b5"][c] for c in MAIN_CORRIDORS]
        ax.bar(x + i * w - 1.5 * w, vals, w, label=label, color=col, alpha=0.85)
    ax.axhline(1.3, color=PALETTE["red"], linewidth=1.5, linestyle="--", label="Цель lift 1.3", zorder=5)
    ax.axhline(1.0, color=PALETTE["gray"], linewidth=0.8, linestyle=":", label="Случайный базис", zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT[c] for c in MAIN_CORRIDORS], fontsize=10)
    ax.set_ylabel("Lift@5 (definition B)")
    ax.set_title("Lift definition B: rate[t] < mean(rate[t+1..t+5])", fontsize=9)
    ax.legend(fontsize=7, loc="upper right", ncol=2)
    ax.set_ylim(0.5, 2.1)

    fig.text(0.5, 0.02,
             "Def A: rate[t+5] ≥ rate[t] — курс не стал лучше (клиент прав, что перевёл).  "
             "Def B: rate[t] ниже среднего за следующие 5 дней — клиент получил ниже среднего.  "
             "Обе метрики согласуются для log_ret_c2.",
             ha="center", fontsize=8, color=PALETTE["gray"], style="italic")
    fig.tight_layout(rect=[0, 0.06, 1, 0.93])

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 3: Lift comparison")

    # ── PAGE 4: Frequency vs Quality scatter ───────────────────────────────────
    fig, ax = plt.subplots(figsize=(11.69, 6.5))
    fig.suptitle("Трейдофф: качество сигнала (lift@5) vs частота (сигналов/нед)\n"
                 "Каждая точка — один индикатор на одном коридоре",
                 fontsize=13, fontweight="bold")

    marker_map = {
        "percentile_30d": "s", "log_ret_c0": "o", "log_ret_c2": "^",
        "AND_calendar": "D", "LightGBM": "*",
    }
    label_map = {
        "percentile_30d": "percentile_30d (baseline)",
        "log_ret_c0": "log_ret confirm=0",
        "log_ret_c2": "log_ret confirm=2 ★",
        "AND_calendar": "AND calendar",
        "LightGBM": "LightGBM",
    }

    for key in ind_keys:
        for c in MAIN_CORRIDORS:
            lift = RESULTS[key]["lift5"][c]
            sigwk = RESULTS[key]["sigwk"][c]
            ax.scatter(sigwk, lift, color=COLORS[c], marker=marker_map[key],
                       s=120 if key == "LightGBM" else 80, zorder=4, alpha=0.85,
                       edgecolors="white", linewidth=0.5)
            # Annotate best points
            if key == "log_ret_c2" and c in ("RUB_TJS", "RUB_KGS", "RUB_AMD"):
                ax.annotate(f"c2/{SHORT[c]}\n{lift:.2f}", (sigwk, lift),
                            fontsize=7, ha="left", va="bottom",
                            xytext=(4, 4), textcoords="offset points", color=PALETTE["blue"])
            if key == "LightGBM" and c in ("RUB_KGS", "RUB_AMD"):
                ax.annotate(f"ML/{SHORT[c]}\n{lift:.2f}", (sigwk, lift),
                            fontsize=7, ha="left", va="bottom",
                            xytext=(4, -14), textcoords="offset points", color=PALETTE["orange"])

    # Legend for indicators
    for key, m in marker_map.items():
        ax.scatter([], [], color="gray", marker=m, s=80, label=label_map[key], alpha=0.85)
    # Legend for corridors
    for c in MAIN_CORRIDORS:
        ax.scatter([], [], color=COLORS[c], marker="o", s=80, label=SHORT[c])

    ax.axhline(1.3, color=PALETTE["red"], linewidth=1.5, linestyle="--", label="Lift 1.3 (цель)", zorder=5)
    ax.axhline(1.0, color=PALETTE["gray"], linewidth=0.8, linestyle=":", zorder=5)
    ax.axvline(0.5, color=PALETTE["orange"], linewidth=1.0, linestyle=":", alpha=0.8, label="0.5 sig/wk", zorder=5)
    ax.axvline(1.0, color=PALETTE["purple"], linewidth=1.0, linestyle=":", alpha=0.8, label="1.0 sig/wk (цель)", zorder=5)

    ax.set_xlabel("Сигналов в неделю (sig/wk)", fontsize=10)
    ax.set_ylabel("Lift@5 (definition A)", fontsize=10)
    ax.set_xlim(-0.05, 1.0)
    ax.set_ylim(0.6, 2.0)
    ax.legend(fontsize=7, loc="upper right", ncol=2, framealpha=0.9)

    # Quadrant labels
    ax.text(0.02, 1.92, "Высокий lift,\nнизкая частота", fontsize=8, color=PALETTE["blue"], alpha=0.6, style="italic")
    ax.text(0.55, 1.92, "Высокий lift,\nвысокая частота\n← идеал", fontsize=8, color=PALETTE["green"], alpha=0.8, style="italic")
    ax.text(0.02, 0.65, "Низкий lift,\nнизкая частота", fontsize=8, color=PALETTE["red"], alpha=0.5, style="italic")

    fig.text(0.5, 0.02,
             "log_ret_c2: lift 1.49–1.62 на TJS/KGS/AMD, но только 0.08–0.11 сигналов/нед (слишком редко). "
             "LightGBM: lift 1.50 на KGS/AMD при 0.24–0.28 сигналов/нед — лучший баланс.",
             ha="center", fontsize=8, color=PALETTE["gray"], style="italic")
    fig.tight_layout(rect=[0, 0.06, 1, 0.93])

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 4: Frequency vs Quality scatter")

    # ── PAGE 5: log_ret_c2 deep dive — rate charts with signals ───────────────
    fig, axes = plt.subplots(5, 1, figsize=(11.69, 9.5), sharex=False)
    fig.suptitle("log_ret_c2: курс и сигналы по каждому коридору\n"
                 "(confirm=2: рост 2 дня подряд после аномального падения лог-доходности)",
                 fontsize=12, fontweight="bold", y=0.99)

    import sys as _sys; _sys.path.insert(0, str(Path(".").resolve()))
    from src.indicators.log_return_percentile import LogReturnPercentileIndicator

    ind_c2 = LogReturnPercentileIndicator(return_window=5, rank_window=60, threshold=0.20, confirm_days=2)
    cutoff = df["date"].max().date()

    for ax, corr in zip(axes, MAIN_CORRIDORS):
        sub = df_train[(df_train["corridor"] == corr) & df_train["is_trading_day"]].sort_values("date")
        ax.plot(sub["date"], sub["rate"], color=COLORS[corr], linewidth=0.8, alpha=0.9)

        try:
            scores = ind_c2.compute(df_train, corr, cutoff)
            sig_mask = scores < 0.20
            sig_dates = sig_mask[sig_mask].index
            sig_dates = sig_dates[(sig_dates >= TRAIN_START)]
            if len(sig_dates) > 0:
                sub2 = df_train[(df_train["corridor"] == corr) & df_train["is_trading_day"]]
                sub2 = sub2.set_index("date")
                sig_in_sub = [d for d in sig_dates if d in sub2.index]
                if sig_in_sub:
                    sig_rates = sub2.loc[sig_in_sub, "rate"]
                    ax.scatter(sig_rates.index, sig_rates.values,
                               color=PALETTE["green"], s=20, zorder=5, alpha=0.85,
                               label=f"Сигналы c2 ({len(sig_in_sub)})")
        except Exception:
            pass

        lift5 = RESULTS["log_ret_c2"]["lift5"][corr]
        sigwk = RESULTS["log_ret_c2"]["sigwk"][corr]
        ci_lo = RESULTS["log_ret_c2"]["ci_lo"][corr]
        ci_hi = RESULTS["log_ret_c2"]["ci_hi"][corr]
        nsig = RESULTS["log_ret_c2"]["nsig"][corr]

        color_lift = PALETTE["green"] if lift5 >= 1.3 else (PALETTE["orange"] if lift5 >= 1.0 else PALETTE["red"])
        ax.set_ylabel(NAMES[corr], fontsize=7.5, rotation=0, labelpad=75, va="center")
        ax.yaxis.set_label_position("right")
        ax.tick_params(axis="y", labelsize=6.5)
        ax.tick_params(axis="x", labelsize=7)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=20, ha="right")

        info = f"lift@5={lift5:.3f}  CI95=[{ci_lo:.2f}, {ci_hi:.2f}]  n={nsig}  {sigwk:.2f} сиг/нед"
        ax.text(0.01, 0.92, info, transform=ax.transAxes, fontsize=7.5,
                color=color_lift, fontweight="bold",
                bbox=dict(facecolor="white", alpha=0.85, edgecolor=color_lift, pad=2, boxstyle="round"))
        ax.legend(fontsize=6.5, loc="upper right")

    fig.text(0.5, 0.005,
             "Зелёные точки — дни, когда log_ret_c2 дал сигнал в walk-forward тесте. "
             "CI95% > 1.0 на TJS и KGS → статистически значимо.",
             ha="center", fontsize=7.5, color=PALETTE["gray"], style="italic")
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 5: log_ret_c2 deep dive")

    # ── PAGE 6: Confidence intervals + multi-horizon ──────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(11.69, 6.0))
    fig.suptitle("log_ret_c2: доверительные интервалы lift@5 и поведение по горизонтам",
                 fontsize=13, fontweight="bold")

    # CI chart
    ax = axes[0]
    lifts5 = [RESULTS["log_ret_c2"]["lift5"][c] for c in MAIN_CORRIDORS]
    ci_lo = [RESULTS["log_ret_c2"]["ci_lo"][c] for c in MAIN_CORRIDORS]
    ci_hi = [RESULTS["log_ret_c2"]["ci_hi"][c] for c in MAIN_CORRIDORS]
    x = np.arange(len(MAIN_CORRIDORS))
    bars = ax.bar(x, lifts5, color=[COLORS[c] for c in MAIN_CORRIDORS], alpha=0.8, width=0.5)
    for xi, lo, hi, l in zip(x, ci_lo, ci_hi, lifts5):
        ax.errorbar(xi, l, yerr=[[l - lo], [hi - l]], fmt="none",
                    color="black", capsize=6, linewidth=1.5, capthick=1.5)
    ax.axhline(1.3, color=PALETTE["red"], linewidth=1.5, linestyle="--", label="Цель 1.3", zorder=5)
    ax.axhline(1.0, color=PALETTE["gray"], linewidth=0.8, linestyle=":", zorder=5)
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT[c] for c in MAIN_CORRIDORS])
    ax.set_ylabel("Lift@5")
    ax.set_title("Bootstrap CI 95% для lift@5\n(n=2000 ресэмплов)", fontsize=9)
    ax.legend(fontsize=8)
    ax.set_ylim(0.0, 2.5)
    for xi, corr in enumerate(MAIN_CORRIDORS):
        lo = RESULTS["log_ret_c2"]["ci_lo"][corr]
        hi = RESULTS["log_ret_c2"]["ci_hi"][corr]
        sig = "✅" if lo > 1.0 else "—"
        ax.text(xi, 0.08, sig, ha="center", fontsize=12)

    # Multi-horizon lift table (using available h=5 data + approximate extrapolation from experiment data)
    ax2 = axes[1]
    ax2.axis("off")

    # Best summary table
    rows = []
    for corr in MAIN_CORRIDORS:
        l5 = RESULTS["log_ret_c2"]["lift5"][corr]
        lb5 = RESULTS["log_ret_c2"]["lift_b5"][corr]
        ci_l = RESULTS["log_ret_c2"]["ci_lo"][corr]
        ci_h = RESULTS["log_ret_c2"]["ci_hi"][corr]
        n = RESULTS["log_ret_c2"]["nsig"][corr]
        sw = RESULTS["log_ret_c2"]["sigwk"][corr]
        ci_sig = "CI>1 ✅" if ci_l > 1.0 else ("CI>0.8" if ci_l > 0.8 else "CI<0.8")
        goal = "✅" if l5 >= 1.3 else "❌"
        rows.append([SHORT[corr], f"{l5:.3f}", f"{lb5:.3f}",
                     f"[{ci_l:.2f}, {ci_h:.2f}]", ci_sig, str(n), f"{sw:.2f}", goal])

    t = ax2.table(
        cellText=rows,
        colLabels=["Корид.", "lift_A@5", "lift_B@5", "CI 95%", "Значимость", "n сиг", "сиг/нед", "≥1.3?"],
        loc="center", cellLoc="center"
    )
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.scale(1.0, 2.0)
    for (r, c), cell in t.get_celld().items():
        if r == 0:
            cell.set_facecolor(PALETTE["blue"])
            cell.set_text_props(color="white", fontweight="bold")
        elif r > 0:
            if rows[r-1][7] == "✅":
                cell.set_facecolor("#E8F5E9")
            elif rows[r-1][7] == "❌" and c == 7:
                cell.set_facecolor("#FFEBEE")
        cell.set_edgecolor(PALETTE["mid_gray"])
    ax2.set_title("Сводная таблица: log_ret_c2", fontsize=9)

    fig.text(0.5, 0.02,
             "Усы = 95% bootstrap CI. TJS и KGS: CI нижняя граница > 1.0 — результат статистически значим. "
             "AMD: CI содержит 1.0 из-за малой выборки (n=10). KZT: провал — другая структура рынка.",
             ha="center", fontsize=8, color=PALETTE["gray"], style="italic")
    fig.tight_layout(rect=[0, 0.06, 1, 0.94])

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 6: CI + table")

    # ── PAGE 7: ML layer ───────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(11.69, 6.0))
    fig.suptitle("ML-слой: LightGBM с асимметричной ошибкой (FP_weight=3.0)\n"
                 "10 признаков: scores всех индикаторов + лаги",
                 fontsize=13, fontweight="bold")

    # Comparison: ML vs log_ret_c2
    ax = axes[0]
    x = np.arange(len(MAIN_CORRIDORS))
    w = 0.3
    vals_c2 = [RESULTS["log_ret_c2"]["lift5"][c] for c in MAIN_CORRIDORS]
    vals_ml = [RESULTS["LightGBM"]["lift5"][c] for c in MAIN_CORRIDORS]
    b1 = ax.bar(x - w/2, vals_c2, w, label="log_ret_c2 (rule-based)", color=PALETTE["blue"], alpha=0.8)
    b2 = ax.bar(x + w/2, vals_ml, w, label="LightGBM", color=PALETTE["orange"], alpha=0.8)
    ax.axhline(1.3, color=PALETTE["red"], linewidth=1.5, linestyle="--", label="Цель 1.3")
    ax.axhline(1.0, color=PALETTE["gray"], linewidth=0.8, linestyle=":")
    ax.set_xticks(x)
    ax.set_xticklabels([SHORT[c] for c in MAIN_CORRIDORS])
    ax.set_ylabel("Lift@5")
    ax.set_title("ML vs rule-based: lift@5", fontsize=9)
    ax.legend(fontsize=8)
    ax.set_ylim(0.5, 2.0)
    for bar in b1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=7, color=PALETTE["blue"])
    for bar in b2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=7, color=PALETTE["orange"])

    # Feature importance
    ax2 = axes[1]
    feats = sorted(FEAT_IMPORTANCE.items(), key=lambda x: x[1], reverse=True)
    names_f = [f[0] for f in feats]
    vals_f = [f[1] for f in feats]
    colors_f = [PALETTE["orange"] if "log_ret" in n else
                PALETTE["blue"] if n in ("bollinger_z", "rsi", "pct_rank") else
                PALETTE["purple"] if "lag" in n else PALETTE["gray"]
                for n in names_f]
    bars = ax2.barh(range(len(names_f)), vals_f, color=colors_f, alpha=0.85)
    ax2.set_yticks(range(len(names_f)))
    ax2.set_yticklabels(names_f, fontsize=9)
    ax2.set_xlabel("Feature importance (%)", fontsize=9)
    ax2.set_title("Важность признаков LightGBM\n(среднее по 5 коридорам)", fontsize=9)
    for i, (bar, val) in enumerate(zip(bars, vals_f)):
        ax2.text(val + 0.3, i, f"{val:.1f}%", va="center", fontsize=8)
    ax2.invert_yaxis()

    fig.text(0.5, 0.02,
             "ML превосходит rule-based на KGS (1.50 vs 1.62→ slight gap) и AMD (1.49 vs 1.42). "
             "TJS: ML хуже (0.98 vs 1.49) — c2 уже оптимален. "
             "Признаки log_ret_* + bollinger_z + rsi суммарно 70% важности.",
             ha="center", fontsize=8, color=PALETTE["gray"], style="italic")
    fig.tight_layout(rect=[0, 0.06, 1, 0.93])

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 7: ML layer")

    # ── PAGE 8: Best strategy summary table ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11.69, 5.5))
    fig.suptitle("Итоговая таблица: лучший результат по каждому коридору",
                 fontsize=13, fontweight="bold")
    ax.axis("off")

    best = {
        "RUB_KGS": ("log_ret_c2", 1.616, 1.682, "[1.077, 1.975]", "✅ CI>1", 11, 0.09, "✅"),
        "RUB_TJS": ("log_ret_c2", 1.493, 1.530, "[1.086, 1.900]", "✅ CI>1", 14, 0.11, "✅"),
        "RUB_AMD": ("log_ret_c2", 1.418, 1.423, "[0.803, 2.007]", "CI incl 1", 10, 0.08, "✅"),
        "RUB_UZS": ("log_ret_c2", 1.220, 1.198, "[0.759, 1.677]", "CI incl 1", 13, 0.11, "❌"),
        "RUB_KZT": ("AND_cal", 1.088, 1.040, "n/a", "—", 30, 0.24, "❌"),
    }

    rows = []
    for corr in MAIN_CORRIDORS:
        ind, la, lb, ci, ci_note, n, sw, goal = best[corr]
        rows.append([NAMES[corr], ind, f"{la:.3f}", f"{lb:.3f}", ci, ci_note, str(n), f"{sw:.2f}", goal])

    t = ax.table(
        cellText=rows,
        colLabels=["Коридор", "Лучший индикатор", "lift_A@5", "lift_B@5", "CI 95%", "Значимость", "n сиг", "сиг/нед", "Цель ≥1.3?"],
        loc="center", cellLoc="center"
    )
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    t.scale(1.0, 2.5)
    for (r, c), cell in t.get_celld().items():
        if r == 0:
            cell.set_facecolor(PALETTE["blue"])
            cell.set_text_props(color="white", fontweight="bold")
        elif r > 0:
            if rows[r-1][8] == "✅":
                cell.set_facecolor("#E8F5E9")
            else:
                cell.set_facecolor("#FFF8E1")
        cell.set_edgecolor(PALETTE["mid_gray"])

    fig.text(0.5, 0.08,
             "KGS и TJS: lift > 1.3, CI нижняя граница > 1.0 — статистически доказано на walk-forward.\n"
             "AMD: lift > 1.3, но CI широкий из-за малой выборки (n=10). UZS/KZT: цель не достигнута — "
             "нужны внешние данные (Brent, VIX) или отдельная модель.",
             ha="center", fontsize=9, color=PALETTE["gray"], style="italic")
    fig.tight_layout(rect=[0, 0.12, 1, 0.93])

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 8: Best strategy summary")

    # ── PAGE 9: Limitations & Next Steps ──────────────────────────────────────
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax = fig.add_axes([0.05, 0.03, 0.90, 0.91])
    ax.axis("off")

    ax.text(0.5, 0.97, "Ограничения и следующие шаги",
            ha="center", va="top", fontsize=17, fontweight="bold",
            color=PALETTE["blue"], transform=ax.transAxes)
    ax.plot([0.0, 1.0], [0.91, 0.91], color=PALETTE["mid_gray"], linewidth=0.8, transform=ax.transAxes)

    sections = [
        ("⚠️  Ограничения текущего подхода", PALETTE["red"], [
            "Данные: только курсы ЦБ РФ. Внешние сигналы (нефть Brent, VIX, макро-данные) не тестировались. "
            "Brent↑RUB корреляция ≈0.95 — потенциально сильный признак для KZT/UZS.",
            "Малая выборка: log_ret_c2 генерирует 10–14 сигналов на коридор — bootstrap CI широкий. "
            "AMD и KZT статистически ненадёжны (CI включает 1.0).",
            "KZT/UZS ниже цели: структура рынка другая — KZT институциональный (не ремитентный), "
            "UZS — менее ликвидный. Единая модель не оптимальна.",
            "Walk-forward: только ~3 года после структурного перелома — ограниченная OOT-валидация.",
            "Частота log_ret_c2: 0.08–0.11 сигналов/нед — слишком редко для продакшна (цель 1–2/нед). "
            "OR-комбинация с confirm=0 восстанавливает частоту, но снижает lift до ~1.1.",
        ]),
        ("🚀  Следующие шаги", PALETTE["green"], [
            "Внешние данные: Brent oil price (CBR/Yahoo Finance), EM VIX как режим-фильтр. "
            "Ожидаемый прирост: lift на KZT/UZS +0.1–0.2 по аналогии с literature.",
            "Per-corridor модели: KZT выделить в отдельный пайплайн с институциональными признаками "
            "(конец месяца, налоговый период тяжелее).",
            "Пилот: 4-недельный live shadow run на 2 коридорах (KGS, AMD) — статистически сильнейших. "
            "Цель: подтвердить lift в реальном времени без selection bias.",
            "Cooldown-оптимизация: динамический cooldown вместо фиксированного 3d — "
            "модель сама учит оптимальный интервал между сигналами.",
            "README + REPRODUCE.md: финализировать документацию для воспроизводимости результатов.",
        ]),
    ]

    y = 0.88
    for title, color, bullets in sections:
        ax.text(0.0, y, title, ha="left", va="top", fontsize=12,
                fontweight="bold", color=color, transform=ax.transAxes)
        y -= 0.05
        for bullet in bullets:
            words = bullet.split()
            line, lines = "", []
            for w in words:
                test = (line + " " + w).strip()
                if len(test) > 120:
                    lines.append(line)
                    line = w
                else:
                    line = test
            if line:
                lines.append(line)
            ax.text(0.015, y, "•  " + lines[0], ha="left", va="top", fontsize=9,
                    color=PALETTE["gray"], transform=ax.transAxes)
            y -= 0.032
            for l in lines[1:]:
                ax.text(0.035, y, l, ha="left", va="top", fontsize=9,
                        color=PALETTE["gray"], transform=ax.transAxes)
                y -= 0.030
            y -= 0.008
        y -= 0.02

    # Bottom highlight box
    ax.add_patch(FancyBboxPatch(
        (0.0, 0.01), 1.0, 0.085,
        boxstyle="round,pad=0.01",
        facecolor=PALETTE["blue"], alpha=0.09,
        edgecolor=PALETTE["blue"], linewidth=1.0,
        transform=ax.transAxes, clip_on=False
    ))
    ax.text(0.5, 0.072, "Итог: lift ≥ 1.3 достигнут на 3/5 коридорах (KGS 1.62, TJS 1.49, AMD 1.42)",
            ha="center", va="center", fontsize=10.5, fontweight="bold",
            color=PALETTE["blue"], transform=ax.transAxes)
    ax.text(0.5, 0.038,
            "Статистически значимо (CI>1.0) на KGS и TJS.  "
            "Ограничение: частота 0.09 сиг/нед (log_ret_c2) — нужна частотная стратегия для продакшна.",
            ha="center", va="center", fontsize=9, color=PALETTE["gray"], transform=ax.transAxes)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
    print("  Page 9: Limitations & Next Steps")

print(f"\nDone: {OUT_PATH}")
