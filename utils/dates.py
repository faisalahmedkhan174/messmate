import calendar
from datetime import date, datetime

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

SHORT_MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
]


def days_in_month(year, month):
    """Accurately calculates total days in a given month, correctly respecting leap years."""
    return calendar.monthrange(year, month)[1]


def month_date_range(year, month):
    """Returns the (first_day, last_day) date objects for a given year and month."""
    last_day = days_in_month(year, month)
    return date(year, month, 1), date(year, month, last_day)


def parse_date(value, default=None):
    """Parse a YYYY-MM-DD string into a date object safely."""
    if not value:
        return default or date.today()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default or date.today()


def get_month_name(month_num):
    """Return full month name (1 -> January)."""
    if 1 <= month_num <= 12:
        return MONTH_NAMES[month_num - 1]
    return ""


def get_short_month_name(month_num):
    """Return 3-letter month name (1 -> Jan)."""
    if 1 <= month_num <= 12:
        return SHORT_MONTH_NAMES[month_num - 1]
    return ""
