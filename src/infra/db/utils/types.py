"""
SQLAlchemy typing utilities.
"""

import typing

from sqlalchemy import orm
from sqlalchemy.ext.asyncio import AsyncSession

SessionFactory = typing.Callable[..., typing.ContextManager[orm.Session]]
SessionGenerator = typing.Generator[orm.Session, None, None]
AsyncSessionFactory = typing.Callable[..., typing.AsyncContextManager[AsyncSession]]
AsyncSessionGenerator = typing.AsyncGenerator[AsyncSession, None]
