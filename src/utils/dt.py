"""
Datetime utilities.
"""

from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone


def month_interval(today: datetime) -> tuple[date, date]:
    first_day = today.replace(day=1)
    next_month = first_day.replace(month=first_day.month + 1)

    last_day = next_month - timedelta(days=1)
    upper_bound = (datetime.min + timedelta(days=1) - timedelta(microseconds=1)).time()
    last_day = datetime.combine(last_day.date(), upper_bound)
    return first_day, last_day


def day_interval(today: datetime) -> tuple[datetime, datetime]:
    begin = datetime.combine(today.date(), datetime.min.time())
    upper_bound = (datetime.min + timedelta(days=1) - timedelta(microseconds=1)).time()
    end = datetime.combine(today.date(), upper_bound)
    return begin, end


def get_utc_now() -> datetime:
    """
    Returns UTC datetime.
    """
    return datetime.now(tz=timezone.utc)
