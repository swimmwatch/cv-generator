import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core import dal


@pytest.fixture
def user_repo(async_db_session: AsyncSession) -> dal.UserAsyncDAL:
    return dal.UserAsyncDAL(async_db_session)
