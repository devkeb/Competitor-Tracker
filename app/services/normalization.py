import re
from decimal import Decimal, InvalidOperation


CURRENCY_SYMBOLS = {
    "₱": "PHP",
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
}


def normalize_text(value: str | None) -> str | None:
    """Remove repeated whitespace from extracted text."""

    if value is None:
        return None

    normalized = " ".join(value.split())
    return normalized or None


def extract_currency(value: str | None) -> str | None:
    """Detect a three-letter currency code from a price string."""

    normalized = normalize_text(value)
    if not normalized:
        return None

    for symbol, currency_code in CURRENCY_SYMBOLS.items():
        if symbol in normalized:
            return currency_code

    upper_value = normalized.upper()

    for currency_code in ("PHP", "USD", "EUR", "GBP"):
        if currency_code in upper_value:
            return currency_code

    return None


def normalize_money(
    value: str | int | float | Decimal | None,
) -> Decimal | None:
    """Convert an extracted monetary value into Decimal."""

    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        return Decimal(str(value))

    normalized = normalize_text(value)
    if not normalized:
        return None

    cleaned = re.sub(r"[^\d.,-]", "", normalized)
    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) == 3:
            cleaned = "".join(parts)
        else:
            cleaned = cleaned.replace(",", ".")

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
