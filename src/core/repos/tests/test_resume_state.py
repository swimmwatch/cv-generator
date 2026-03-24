import uuid

import fakeredis

from core import repos


class TestRedisResumeStateRepositorySetActive:
    async def test_sets_active_state(
        self,
        redis_resume_state_repo: repos.RedisResumeStateRepository,
    ) -> None:
        user_id = uuid.uuid4()

        await redis_resume_state_repo.set_active(user_id)

        assert await redis_resume_state_repo.is_active(user_id) is True

    async def test_set_active_is_idempotent(
        self,
        redis_resume_state_repo: repos.RedisResumeStateRepository,
    ) -> None:
        user_id = uuid.uuid4()

        await redis_resume_state_repo.set_active(user_id)
        await redis_resume_state_repo.set_active(user_id)

        assert await redis_resume_state_repo.is_active(user_id) is True


class TestRedisResumeStateRepositoryClearActive:
    async def test_clears_active_state(
        self,
        redis_resume_state_repo: repos.RedisResumeStateRepository,
    ) -> None:
        user_id = uuid.uuid4()
        await redis_resume_state_repo.set_active(user_id)

        await redis_resume_state_repo.clear_active(user_id)

        assert await redis_resume_state_repo.is_active(user_id) is False

    async def test_clear_nonexistent_does_not_raise(
        self,
        redis_resume_state_repo: repos.RedisResumeStateRepository,
    ) -> None:
        user_id = uuid.uuid4()

        await redis_resume_state_repo.clear_active(user_id)

        assert await redis_resume_state_repo.is_active(user_id) is False


class TestRedisResumeStateRepositoryIsActive:
    async def test_returns_false_when_not_set(
        self,
        redis_resume_state_repo: repos.RedisResumeStateRepository,
    ) -> None:
        user_id = uuid.uuid4()

        assert await redis_resume_state_repo.is_active(user_id) is False

    async def test_returns_true_when_set(
        self,
        redis_resume_state_repo: repos.RedisResumeStateRepository,
    ) -> None:
        user_id = uuid.uuid4()
        await redis_resume_state_repo.set_active(user_id)

        assert await redis_resume_state_repo.is_active(user_id) is True

    async def test_different_users_are_independent(
        self,
        redis_resume_state_repo: repos.RedisResumeStateRepository,
    ) -> None:
        user1 = uuid.uuid4()
        user2 = uuid.uuid4()

        await redis_resume_state_repo.set_active(user1)

        assert await redis_resume_state_repo.is_active(user1) is True
        assert await redis_resume_state_repo.is_active(user2) is False

    async def test_returns_false_after_ttl_expires(
        self,
        async_redis_client: fakeredis.FakeAsyncRedis,
    ) -> None:
        repo = repos.RedisResumeStateRepository(async_redis_client)
        user_id = uuid.uuid4()
        await repo.set_active(user_id)

        key = f"resume_processing:{user_id}"
        ttl = await async_redis_client.ttl(key)

        assert ttl > 0
