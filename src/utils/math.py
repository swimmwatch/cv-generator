"""
Math utilities.
"""

import uuid


def prev_interval(begin, end) -> tuple:
    """
    Returns previous interval.
    """
    if end < begin:
        raise ValueError("end must be greater or equal then begin")
    diff = delta(begin, end)
    return begin - diff, end - diff


def delta(a, b):
    """
    Returns difference between `a` and `b`
    """
    lower, upper = sorted([a, b])
    return upper - lower


def unique_int(bit: int = 32):
    return uuid.uuid4().int & (1 << bit) - 1
