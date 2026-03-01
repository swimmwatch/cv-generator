import typing
from types import TracebackType

import redis
import redis.asyncio as aioredis

from infra.logger.utils import get_logger
from utils.transactions.manager import BaseAsyncTransactionManager
from utils.transactions.manager import BaseTransactionManager

logger = get_logger(__name__)


class RedisTransactionManager(BaseTransactionManager):
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis_client = redis_client

    def __enter__(self) -> typing.Self:
        self._redis_client.execute_command("MULTI")
        logger.debug("Redis transaction was started")

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self._redis_client.execute_command("DISCARD")
            logger.debug("Redis transaction was rolled back")
        else:
            self._redis_client.execute_command("EXEC")
            logger.debug("Redis transaction was committed")


class AsyncRedisTransactionManager(BaseAsyncTransactionManager):
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis_client = redis_client

    async def __aenter__(self) -> typing.Self:
        await self._redis_client.execute_command("MULTI")
        logger.debug("Redis transaction was started")

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self._redis_client.execute_command("DISCARD")
            logger.debug("Redis transaction was rolled back")
        else:
            await self._redis_client.execute_command("EXEC")
            logger.debug("Redis transaction was committed")
