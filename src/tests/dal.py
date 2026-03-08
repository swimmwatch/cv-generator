import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core import dal


@pytest.fixture
def sql_user_dal(async_db_session: AsyncSession) -> dal.UserAsyncDAL:
    return dal.UserAsyncDAL(async_db_session)
