import typing

from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.client import AsyncDatabase
from infra.logger.utils import get_logger

logger = get_logger(__name__)


async def init_session(db: AsyncDatabase) -> typing.AsyncGenerator[AsyncSession, None]:
    async with db.session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            logger.debug("Database session was rolled back due to exception")
            raise
        else:
            await session.commit()
            logger.debug("Database session was committed")
