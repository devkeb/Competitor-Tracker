import re
from decimal import Decimal, InvalidOperation


CURRENCY_SYMBOLS = {
    "₱": "PHP",
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
}


def normalize_text(value: str | None) -> str | None:
    """Remove extra whitespace from extracted text."""

    if value is None:
        return None

    normalized = " ".join(value.split())

    return normalized or None


def normalize_currency(value: str | None) -> str | None:
    """
    Convert a currency symbol or currency name into a three-letter code.

    Examples:
        ₱       -> PHP
        PHP     -> PHP
        P       -> PHP
        USD     -> USD
    """

    value = normalize_text(value)

    if not value:
        return None

    upper_value = value.upper()

    currency_names = {
        "PHP": "PHP",
        "P": "PHP",
        "PESO": "PHP",
        "PESOS": "PHP",
        "PHILIPPINE PESO": "PHP",
        "USD": "USD",
        "US DOLLAR": "USD",
        "EUR": "EUR",
        "GBP": "GBP",
    }

    if value in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[value]

    return currency_names.get(upper_value)


def extract_currency(value: str | None) -> str | None:
    """
    Detect the currency from a price string.

    Examples:
        ₱7,500          -> PHP
        PHP 7,500       -> PHP
        $120            -> USD
    """

    value = normalize_text(value)

    if not value:
        return None

    for symbol, currency_code in CURRENCY_SYMBOLS.items():
        if symbol in value:
            return currency_code

    upper_value = value.upper()

    if "PHP" in upper_value:
        return "PHP"

    if "USD" in upper_value:
        return "USD"

    if "EUR" in upper_value:
        return "EUR"

    if "GBP" in upper_value:
        return "GBP"

    return None


def normalize_money(value: str | int | float | Decimal | None) -> Decimal | None:
    """
    Convert an extracted price into Decimal.

    Examples:
        "₱7,500"          -> Decimal("7500")
        "PHP 8,350.50"    -> Decimal("8350.50")
        "1,250"           -> Decimal("1250")
    """

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

    # Assume commas are thousands separators when a period is present.
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")

    # Handle common thousands separator format, such as 7,500.
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


def normalize_integer(value: str | int | None) -> int | None:
    """
    Extract an integer from text.

    Examples:
        "32 reviews"       -> 32
        "Maximum 15 guests" -> 15
        "1,245 reviews"    -> 1245
    """

    if value is None:
        return None

    if isinstance(value, int):
        return value

    normalized = normalize_text(value)

    if not normalized:
        return None

    match = re.search(r"-?[\d,]+", normalized)

    if not match:
        return None

    try:
        return int(match.group().replace(",", ""))
    except ValueError:
        return None


def normalize_rating(value: str | float | Decimal | None) -> Decimal | None:
    """
    Convert a rating into a Decimal between 0 and 5.

    Examples:
        "4.89"            -> Decimal("4.89")
        "Rated 4.7 out of 5" -> Decimal("4.7")
    """

    if value is None:
        return None

    if isinstance(value, Decimal):
        rating = value
    elif isinstance(value, (int, float)):
        rating = Decimal(str(value))
    else:
        normalized = normalize_text(value)

        if not normalized:
            return None

        match = re.search(r"\d+(?:\.\d+)?", normalized)

        if not match:
            return None

        try:
            rating = Decimal(match.group())
        except InvalidOperation:
            return None

    if rating < 0 or rating > 5:
        return None

    return rating


def normalize_status(
    available: bool | None,
    error: bool = False,
) -> str:
    """
    Convert availability evidence into a database status.

    Returns:
        available
        not_bookable
        unknown
        error
    """

    if error:
        return "error"

    if available is True:
        return "available"

    if available is False:
        return "not_bookable"

    return "unknown"


def normalize_minimum_nights(value: str | int | None) -> int | None:
    """
    Extract the minimum number of nights.

    Examples:
        "2-night minimum"    -> 2
        "Minimum stay: 3 nights" -> 3
    """

    nights = normalize_integer(value)

    if nights is None or nights < 1:
        return None

    return nights