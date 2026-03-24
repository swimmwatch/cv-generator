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

    def _key(self, user_id: uuid.UUID) -> str:
        return f"{_JOB_STATE_KEY_PREFIX}{user_id}"

    async def set_active(self, user_id: uuid.UUID) -> None:
        await self._redis_client.set(self._key(user_id), 1, ex=_JOB_STATE_TTL)

    async def clear_active(self, user_id: uuid.UUID) -> None:
        await self._redis_client.delete(self._key(user_id))

    async def is_active(self, user_id: uuid.UUID) -> bool:
        return bool(await self._redis_client.exists(self._key(user_id)))
