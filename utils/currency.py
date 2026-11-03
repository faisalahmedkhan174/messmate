from decimal import Decimal, ROUND_HALF_UP


def round_currency(value, places=2):
    """Safely round financial amounts to 2 decimal places."""
    if value is None:
        return 0.0
    try:
        return round(float(value), places)
    except (TypeError, ValueError):
        return 0.0


def safe_div(numerator, denominator):
    """Safely divide two numbers without division by zero errors."""
    if not denominator:
        return 0.0
    return round_currency(numerator / denominator)


def format_bdt(value):
    """
    Format numeric value as Bangladeshi Taka (৳).
    Preserves exact numeric values for display, handles negative numbers cleanly,
    and prevents broken glyphs.
    Examples:
        1250.0  -> ৳1,250.00
        -450.5  -> -৳450.50
        0       -> ৳0.00
    """
    if value is None or value == "":
        return "\u09f30.00"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    if number < 0:
        return "-\u09f3{:,.2f}".format(abs(number))
    return "\u09f3{:,.2f}".format(number)
