"""Telegram HTML helpers.

This module exists to avoid depending on python-telegram-bot just for helpers.
"""

from __future__ import annotations

import html


def mention_html(user_id: int, name: str) -> str:
    """Build an HTML mention link.

    Matches PTB's telegram.helpers.mention_html behavior closely.
    """

    return f'<a href="tg://user?id={user_id}">{html.escape(name)}</a>'
