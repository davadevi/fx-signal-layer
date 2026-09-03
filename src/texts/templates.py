"""Push text templates and compliance validator.

All texts describe present/past facts only. Predictions, urgency, promises,
and investment framing are forbidden.
"""
from __future__ import annotations

CURRENCY_NAMES: dict[str, tuple[str, str]] = {
    "RUB_TJS": ("сомони", "Таджикистан"),
    "RUB_UZS": ("сум", "Узбекистан"),
    "RUB_KGS": ("сом", "Кыргызстан"),
    "RUB_AMD": ("драм", "Армения"),
    "RUB_KZT": ("тенге", "Казахстан"),
}

FORBIDDEN_PATTERNS: list[str] = [
    "вырастет",
    "подорожает",
    "успейте",
    "пока не",
    "гарантируем",
    "заработайте",
]


def format_push_text(
    corridor: str,
    percentile_rank: float,
    current_rate: float,
    direction: str,
) -> str:
    """Generate compliant push text — present/past facts only."""
    currency_name, _country = CURRENCY_NAMES.get(corridor, (corridor, ""))
    pct = int(round(percentile_rank * 100))
    if direction == "window_closing":
        return (
            f"Курс рубля к {currency_name} растёт третий день. "
            f"Сегодня ещё в нижней четверти за 30 дней ({pct}%). "
            f"Текущий курс: {current_rate:.4f} руб."
        )
    # default: favorable_now
    return (
        f"Курс рубля к {currency_name} — в нижних {pct}% за последние 30 дней. "
        f"Текущий курс: {current_rate:.4f} руб."
    )


def validate_push_text(text: str) -> tuple[bool, list[str]]:
    """Check text against forbidden patterns. Returns (is_valid, violations)."""
    lowered = text.lower()
    violations = [p for p in FORBIDDEN_PATTERNS if p in lowered]
    return (len(violations) == 0, violations)
