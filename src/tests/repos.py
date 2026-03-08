import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core import repos


@pytest.fixture
def sql_user_repo(async_db_session: AsyncSession) -> repos.SqlAlchemyUserRepository:
    return repos.SqlAlchemyUserRepository(async_db_session)
