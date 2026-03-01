import fakeredis

from core import dal
from infra.db.utils.transactions import AsyncSqlAlchemyTransactionManager
from infra.redis.transactions import AsyncRedisTransactionManager
from tests.factories import UserFactory
from utils.transactions.manager import AsyncTransactionManager


class TestAsyncSqlAlchemyTransactionManager:
    async def test_rollback_on_error(
        self,
        user_dal: dal.UserAsyncDAL,
        async_sql_transaction_manager: AsyncSqlAlchemyTransactionManager,
    ) -> None:
        await UserFactory.create_async()

        user = await user_dal.first()
        assert user

        init_value = user.username

        try:
            async with async_sql_transaction_manager:
                await user_dal.filter(id=user.id).update(username=init_value + "_new")
                raise ValueError("Test error")
        except ValueError:
            pass

        updated_user = await user_dal.first()
        assert updated_user.username == init_value

    async def test_updated(
        self,
        user_dal: dal.UserAsyncDAL,
        async_sql_transaction_manager: AsyncSqlAlchemyTransactionManager,
    ) -> None:
        await UserFactory.create_async()

        user = await user_dal.first()
        assert user

        init_value = user.username
        new_value = init_value + "_new"

        async with async_sql_transaction_manager:
            await user_dal.filter(id=user.id).update(username=new_value)

        updated_user = await user_dal.first()
        assert updated_user.username == new_value


class TestAsyncRedisTransactionManager:
    async def test_rollback_on_error(
        self,
        async_redis_client: fakeredis.FakeAsyncRedis,
        async_redis_transaction_manager: AsyncRedisTransactionManager,
    ) -> None:
        key = "test_key"
        init_value = 1
        await async_redis_client.set(key, init_value)

        try:
            async with async_redis_transaction_manager:
                await async_redis_client.incr(key)
                raise ValueError("Test error")
        except ValueError:
            pass

        updated_value = await async_redis_client.get(key)
        updated_value = updated_value.decode("utf-8") if updated_value else None
        updated_value = int(updated_value) if updated_value else None
        assert updated_value == init_value

    async def test_updated(
        self,
        async_redis_client: fakeredis.FakeAsyncRedis,
        async_redis_transaction_manager: AsyncRedisTransactionManager,
    ) -> None:
        key = "test_key"
        init_value = 1
        await async_redis_client.set(key, init_value)
        new_value = init_value + 1

        async with async_redis_transaction_manager:
            await async_redis_client.incr(key)

        updated_value = await async_redis_client.get(key)
        updated_value = updated_value.decode("utf-8") if updated_value else None
        updated_value = int(updated_value) if updated_value else None
        assert updated_value == new_value


class TestSqlAndRedisTransactionManager:
    async def test_all_rollback_on_error(
        self,
        user_dal: dal.UserAsyncDAL,
        async_redis_client: fakeredis.FakeAsyncRedis,
        async_transaction_manager: AsyncTransactionManager,
    ) -> None:
        await UserFactory.create_async()

        user = await user_dal.first()
        assert user

        sql_init_value = user.username

        key = "test_key"
        redis_init_value = 1
        await async_redis_client.set(key, redis_init_value)

        try:
            async with async_transaction_manager:
                await user_dal.filter(id=user.id).update(username=sql_init_value + "_new")
                await async_redis_client.incr(key)
                raise ValueError("Test error")
        except ValueError:
            pass

        updated_user = await user_dal.first()
        assert updated_user.username == sql_init_value

        redis_updated_value = await async_redis_client.get(key)
        redis_updated_value = redis_updated_value.decode("utf-8") if redis_updated_value else None
        redis_updated_value = int(redis_updated_value) if redis_updated_value else None
        assert redis_updated_value == redis_init_value

    async def test_updated(
        self,
        user_dal: dal.UserAsyncDAL,
        async_redis_client: fakeredis.FakeAsyncRedis,
        async_transaction_manager: AsyncTransactionManager,
    ) -> None:
        await UserFactory.create_async()

        user = await user_dal.first()
        assert user

        sql_init_value = user.username
        sql_new_value = sql_init_value + "_new"

        key = "test_key"
        redis_init_value = 1
        redis_new_value = redis_init_value + 1
        await async_redis_client.set(key, redis_init_value)

        async with async_transaction_manager:
            await user_dal.filter(id=user.id).update(username=sql_new_value)
            await async_redis_client.incr(key)

        updated_user = await user_dal.first()
        assert updated_user.username == sql_new_value

        redis_updated_value = await async_redis_client.get(key)
        redis_updated_value = redis_updated_value.decode("utf-8") if redis_updated_value else None
        redis_updated_value = int(redis_updated_value) if redis_updated_value else None
        assert redis_updated_value == redis_new_value
