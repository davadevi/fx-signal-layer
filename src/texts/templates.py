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
    score: float,
    current_rate: float,
    direction: str,
) -> str:
    """Generate compliant push text — present/past facts only.

    score: percentile rank of 5-day log-return in rolling 60-day window.
    Low score = ruble strengthened more than usual recently.
    """
    currency_name, _country = CURRENCY_NAMES.get(corridor, (corridor, ""))
    stronger_pct = int(round((1.0 - score) * 100))
    if direction == "window_closing":
        return (
            f"Рубль укреплялся к {currency_name} несколько дней подряд — "
            f"курс ещё выгоднее, чем в {stronger_pct}% случаев за 3 месяца. "
            f"Текущий курс: {current_rate:.4f} руб."
        )
    # default: favorable_now
    return (
        f"Рубль укрепился к {currency_name} за последние 5 дней "
        f"сильнее, чем в {stronger_pct}% случаев за 3 месяца. "
        f"Текущий курс: {current_rate:.4f} руб."
    )


def validate_push_text(text: str) -> tuple[bool, list[str]]:
    """Check text against forbidden patterns. Returns (is_valid, violations)."""
    lowered = text.lower()
    violations = [p for p in FORBIDDEN_PATTERNS if p in lowered]
    return (len(violations) == 0, violations)
