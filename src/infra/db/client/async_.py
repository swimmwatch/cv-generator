"""
Async database client.
"""

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_scoped_session
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from infra.db.session_scope import scope_func
from infra.db.utils.types import AsyncSessionGenerator
from infra.logger.utils import get_logger

logger = get_logger(__name__)


class AsyncDatabase:
    def __init__(self, db_url: str) -> None:
        self._engine = create_async_engine(
            db_url,
            echo=False,
            echo_pool=False,
        )
        logger.debug("Database engine was created")

        self._session_factory = async_scoped_session(
            async_sessionmaker(
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                bind=self._engine,
            ),
            scope_func,
        )

    @property
    def engine(self) -> AsyncEngine:
        """Return the async engine."""
        return self._engine

    def get_scoped_session(self) -> AsyncSession:
        """Return the async session bound to the current scope."""
        return self._session_factory()

    async def commit_scoped_session(self) -> None:
        try:
            await self.get_scoped_session().commit()
        except Exception:
            logger.debug("Commit failed, attempting rollback")
            await self.get_scoped_session().rollback()
            raise

    async def rollback_scoped_session(self) -> None:
        try:
            await self.get_scoped_session().rollback()
        except Exception:
            logger.debug("Rollback failed")
            raise

    @asynccontextmanager
    async def session(self) -> AsyncSessionGenerator:
        session: AsyncSession = self.get_scoped_session()
        logger.debug("Database session was created")
        yield session

    async def stop(self) -> None:
        await self._engine.dispose()
        logger.debug("Database engine was disposed")

    async def remove_scoped_session(self) -> None:
        await self._session_factory.close()
        await self._session_factory.remove()
        logger.debug("Scoped session remove was called but no session was bound")
