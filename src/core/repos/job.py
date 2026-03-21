import typing
import uuid

from redis.asyncio import Redis

_JOB_STATE_KEY_PREFIX = "job_parsing:"
_JOB_STATE_TTL = 180


class JobStateRepository(typing.Protocol):
    async def set_active(self, user_id: uuid.UUID) -> None:
        pass

    async def clear_active(self, user_id: uuid.UUID) -> None:
        pass

    async def is_active(self, user_id: uuid.UUID) -> bool:
        pass


class RedisJobStateRepository:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def set_active(self, user_id: uuid.UUID) -> None:
        key = f"{_JOB_STATE_KEY_PREFIX}{user_id}"
        await self._redis_client.set(key, 1, ex=_JOB_STATE_TTL)

    async def clear_active(self, user_id: uuid.UUID) -> None:
        key = f"{_JOB_STATE_KEY_PREFIX}{user_id}"
        await self._redis_client.delete(key)

    async def is_active(self, user_id: uuid.UUID) -> bool:
        key = f"{_JOB_STATE_KEY_PREFIX}{user_id}"
        return bool(await self._redis_client.exists(key))
