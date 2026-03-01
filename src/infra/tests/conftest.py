import fakeredis
import pytest
from mongomock_motor import AsyncMongoMockClient
from sqlalchemy import orm
from sqlalchemy.ext.asyncio import AsyncSession

from core import dal
from infra.db.utils.transactions import AsyncSqlAlchemyTransactionManager
from infra.db.utils.transactions import SqlAlchemyTransactionManager
from infra.mongo.transactions import AsyncMongoTransactionManager
from infra.redis.transactions import AsyncRedisTransactionManager
from infra.redis.transactions import RedisTransactionManager
from utils.transactions.manager import AsyncTransactionManager
from utils.transactions.manager import TransactionManager


@pytest.fixture
def sql_transaction_manager(db_session: orm.Session) -> SqlAlchemyTransactionManager:
    return SqlAlchemyTransactionManager(db_session)


@pytest.fixture
def async_sql_transaction_manager(async_db_session: AsyncSession) -> AsyncSqlAlchemyTransactionManager:
    return AsyncSqlAlchemyTransactionManager(async_db_session)


@pytest.fixture
def redis_transaction_manager(redis_client: fakeredis.FakeRedis) -> RedisTransactionManager:
    return RedisTransactionManager(redis_client)


@pytest.fixture
def async_redis_transaction_manager(async_redis_client: fakeredis.FakeAsyncRedis) -> AsyncRedisTransactionManager:
    return AsyncRedisTransactionManager(async_redis_client)


@pytest.fixture
def async_mongo_transaction_manager(async_mongo_client: AsyncMongoMockClient) -> AsyncMongoTransactionManager:
    return AsyncMongoTransactionManager(async_mongo_client)


@pytest.fixture
def transaction_manager(
    sql_transaction_manager: SqlAlchemyTransactionManager,
    redis_transaction_manager: RedisTransactionManager,
) -> TransactionManager:
    return TransactionManager(
        [
            sql_transaction_manager,
            redis_transaction_manager,
        ]
    )


@pytest.fixture
def async_transaction_manager(
    async_sql_transaction_manager: AsyncSqlAlchemyTransactionManager,
    async_redis_transaction_manager: AsyncRedisTransactionManager,
) -> AsyncTransactionManager:
    return AsyncTransactionManager(
        [
            async_sql_transaction_manager,
            async_redis_transaction_manager,
        ]
    )


@pytest.fixture
def user_dal(async_db_session: AsyncSession) -> dal.UserAsyncDAL:
    return dal.UserAsyncDAL(async_db_session)
