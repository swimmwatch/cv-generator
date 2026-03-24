import fakeredis
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core import repos


@pytest.fixture
def sql_user_repo(async_db_session: AsyncSession) -> repos.SqlAlchemyUserRepository:
    return repos.SqlAlchemyUserRepository(async_db_session)


@pytest.fixture
def sql_resume_repo(async_db_session: AsyncSession) -> repos.SqlAlchemyResumeRepository:
    return repos.SqlAlchemyResumeRepository(async_db_session)


@pytest.fixture
def sql_job_repo(async_db_session: AsyncSession) -> repos.SqlAlchemyJobRepository:
    return repos.SqlAlchemyJobRepository(async_db_session)


@pytest.fixture
def sql_generated_cv_repo(async_db_session: AsyncSession) -> repos.SqlAlchemyGeneratedCVRepository:
    return repos.SqlAlchemyGeneratedCVRepository(async_db_session)


@pytest.fixture
def redis_job_state_repo(async_redis_client: fakeredis.FakeAsyncRedis) -> repos.RedisJobStateRepository:
    return repos.RedisJobStateRepository(async_redis_client)


@pytest.fixture
def redis_chat_state_repo(async_redis_client: fakeredis.FakeAsyncRedis) -> repos.RedisChatStateRepository:
    return repos.RedisChatStateRepository(async_redis_client)


@pytest.fixture
def redis_resume_state_repo(async_redis_client: fakeredis.FakeAsyncRedis) -> repos.RedisResumeStateRepository:
    return repos.RedisResumeStateRepository(async_redis_client)


@pytest.fixture
def sql_transaction_repo(async_db_session: AsyncSession) -> repos.SqlAlchemyTransactionRepository:
    return repos.SqlAlchemyTransactionRepository(async_db_session)
