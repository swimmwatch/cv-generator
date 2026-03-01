from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.utils.types import AsyncSessionGenerator
from infra.logger.utils import get_logger

logger = get_logger(__name__)


class TestAsyncDatabase:
    def __init__(
        self,
        engine: AsyncEngine,
        session: AsyncSession,
    ) -> None:
        self._engine = engine
        self._session_factory = session

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    def get_scoped_session(self) -> AsyncSession:
        return self._session_factory

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
        logger.debug("Database engine was disposed")

    async def remove_scoped_session(self) -> None:
        logger.debug("Scoped session remove was called but no session was bound")
