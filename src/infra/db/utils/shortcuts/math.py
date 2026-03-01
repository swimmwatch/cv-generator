"""
SQLAlchemy's math shortcuts.
"""

import operator
from typing import Literal
from typing import Sequence

import sqlalchemy as sa

from utils.math import prev_interval

LessNotation = Literal["lt", "le"]
GreaterNotation = Literal["gt", "ge"]


def interval_filter(
    column,
    begin,
    end,
    less: LessNotation = "le",
    greate: GreaterNotation = "ge",
):
    left_operator = getattr(operator, greate)
    right_operator = getattr(operator, less)

    if end is None:
        return left_operator(column, begin)
    elif begin is None:
        return right_operator(column, end)
    else:
        return sa.and_(
            left_operator(column, begin),
            right_operator(column, end),
        )


def calc_gain(amount, prev_amount) -> sa.Case:
    # convert to float and get absolute value
    prev_amount = sa.func.abs(1.0 * prev_amount)
    amount = sa.func.abs(1.0 * amount)

    return sa.case(
        (
            sa.or_(
                prev_amount == sa.null(),
                amount == sa.null(),
            ),
            None,
        ),
        (
            sa.and_(prev_amount == 0.0, amount == 0.0),
            0.0,
        ),
        (
            prev_amount == 0.0,
            1.0,
        ),
        else_=-1.0 + (amount / prev_amount),
    )


def gain_stmt(
    stmt: sa.Select,
    column,
    begin,
    end,
    columns: Sequence[str],
    postfix: str = "gain",
) -> sa.Select:
    prev_interval_ = prev_interval(begin, end)
    curr_filter = interval_filter(column, begin, end)
    prev_filter = interval_filter(column, *prev_interval_)

    curr_stmt = stmt.filter(curr_filter).cte("current_period")
    prev_stmt = stmt.filter(prev_filter).cte("previous_period")

    curr_cols = (getattr(curr_stmt.c, col) for col in columns)
    extra_cols = (
        calc_gain(
            getattr(curr_stmt.c, col),
            getattr(prev_stmt.c, col),
        ).label(f"{col}_{postfix}")
        for col in columns
    )
    return sa.select(*curr_cols, *extra_cols).select_from(curr_stmt, prev_stmt)
