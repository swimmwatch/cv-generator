"""
Unittests for Datetime utilities.
"""

from datetime import date
from datetime import datetime

import pytest

from utils.dt import day_interval
from utils.dt import month_interval


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (
            datetime(2000, 1, 1),
            (datetime(2000, 1, 1), datetime(2000, 1, 31, 23, 59, 59, 999999)),
        ),
        (
            datetime(2000, 2, 1),
            (datetime(2000, 2, 1), datetime(2000, 2, 29, 23, 59, 59, 999999)),
        ),
        (
            datetime(2001, 2, 1),
            (datetime(2001, 2, 1), datetime(2001, 2, 28, 23, 59, 59, 999999)),
        ),
    ],
)
def test_month_interval(today: datetime, expected: tuple[date, date]):
    assert month_interval(today) == expected


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (
            datetime(2000, 1, 1, 9),
            (datetime(2000, 1, 1, 0, 0, 0), datetime(2000, 1, 1, 23, 59, 59, 999999)),
        ),
    ],
)
def test_day_interval(today: datetime, expected: tuple[datetime, datetime]):
    assert day_interval(today) == expected
