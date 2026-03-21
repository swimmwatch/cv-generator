import typing
from collections.abc import AsyncIterator

from aiogram import Bot
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.client import AsyncDatabase
from infra.logger.utils import get_logger

logger = get_logger(__name__)


async def init_tg_bot(token: str) -> AsyncIterator[Bot]:
    bot = Bot(token=token)
    yield bot
    await bot.session.close()
    logger.debug("Closed Telegram Bot session")


async def init_agent_checkpointer(
    redis_url: str,
    ttl: dict,
) -> AsyncIterator[AsyncRedisSaver]:
    redis_client = AsyncRedis.from_url(redis_url)
    saver = AsyncRedisSaver(redis_client=redis_client, ttl=ttl)
    async with saver:
        yield saver
    logger.debug("Closed Agent Checkpointer session")


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
