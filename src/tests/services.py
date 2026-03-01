import pytest

from core import repos
from core import services


@pytest.fixture
def user_service(sql_user_repo: repos.SqlAlchemyUserRepository) -> services.UserService:
    return services.UserService(sql_user_repo)
