"""
Unittests for Math utilities.
"""

from datetime import date

import pytest

from utils.math import delta
from utils.math import prev_interval


@pytest.mark.parametrize(
    ("interval", "expected"),
    [
        (
            (0, 1),
            (-1, 0),
        ),
        (
            (date(2000, 1, 10), date(2000, 1, 15)),
            (date(2000, 1, 5), date(2000, 1, 10)),
        ),
    ],
)
def test_prev_interval(interval: tuple, expected: tuple):
    actual = prev_interval(*interval)
    assert actual == expected
    assert delta(*actual) == delta(*actual)
