"""
Task-scoped session key handling for SQLAlchemy async_scoped_session.

We bind the session scope to a ContextVar. If the ContextVar is not set (e.g., CLI/tests), we fall back
to the current asyncio task object, preserving previous behavior.
"""

import asyncio
import typing
from contextvars import ContextVar
from contextvars import Token

_SESSION_SCOPE: ContextVar[typing.Any | None] = ContextVar(
    "SESSION_SCOPE",
    default=None,
)

# Fallback global sentinel when no asyncio task exists.
_GLOBAL_SENTINEL = object()


def set_session_scope(value: typing.Any) -> Token[typing.Any | None]:
    """Set the current scope key, return a token for later reset in the same context."""
    return _SESSION_SCOPE.set(value)


def clear_session_scope() -> None:
    """Clear current scope key in this context."""
    _SESSION_SCOPE.set(None)


def reset_session_scope(token: Token[typing.Any | None]) -> None:
    """Reset task scope ContextVar to the previous value using the provided token.

    Be tolerant to cross-context resets: if a token belongs to another context,
    just clear the value in this context to avoid ValueError.
    """
    try:
        _SESSION_SCOPE.reset(token)
    except ValueError:
        # Token was created in another context; best-effort clear in this context.
        clear_session_scope()


def scope_func():
    """Return the current scope key for async_scoped_session."""
    key = _SESSION_SCOPE.get()
    if key is not None:
        return key

    task = asyncio.current_task()
    if task is not None:
        return task

    return _GLOBAL_SENTINEL
