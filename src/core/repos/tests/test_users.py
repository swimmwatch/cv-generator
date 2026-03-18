import uuid

from core import dto
from core import models
from core import repos
from tests.factories import UserFactory


class TestSqlAlchemyUserRepositoryCreateOne:
    async def test_creates_user(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
    ) -> None:
        data = dto.UserCreateDTO(
            messenger_id="12345",
            username="testuser",
            first_name="John",
            last_name="Doe",
            is_superuser=False,
            is_staff=False,
        )
        result = await sql_user_repo.create_one(data)

        assert result.messenger_id == "12345"
        assert result.username == "testuser"
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.is_superuser is False
        assert result.is_staff is False
        assert result.id is not None

    async def test_creates_user_with_optional_fields_none(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
    ) -> None:
        data = dto.UserCreateDTO(
            messenger_id="99999",
            first_name="Solo",
            is_superuser=False,
            is_staff=False,
        )
        result = await sql_user_repo.create_one(data)

        assert result.username is None
        assert result.last_name is None
        assert result.password_hash is None
        assert result.language_code is None

    async def test_creates_superuser(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
    ) -> None:
        pw = "pbkdf2_sha256$hash"  # noqa: S105
        data = dto.UserCreateDTO(
            messenger_id="admin1",
            first_name="Admin",
            is_superuser=True,
            is_staff=True,
            password_hash=pw,
        )
        result = await sql_user_repo.create_one(data)

        assert result.is_superuser is True
        assert result.is_staff is True
        assert result.password_hash == pw


class TestSqlAlchemyUserRepositoryGetByPk:
    async def test_returns_user(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        result = await sql_user_repo.get_by_pk(user.id)

        assert result is not None
        assert result.id == user.id
        assert result.messenger_id == user.messenger_id

    async def test_returns_none_for_nonexistent_pk(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
    ) -> None:
        result = await sql_user_repo.get_by_pk(uuid.uuid4())

        assert result is None


class TestSqlAlchemyUserRepositoryGetByUsername:
    async def test_returns_user(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(username="findme")
        result = await sql_user_repo.get_by_username("findme")

        assert result is not None
        assert result.id == user.id
        assert result.username == "findme"

    async def test_returns_none_for_nonexistent_username(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
    ) -> None:
        result = await sql_user_repo.get_by_username("nonexistent")

        assert result is None


class TestSqlAlchemyUserRepositoryGetByMessengerId:
    async def test_returns_user(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(messenger_id="tg_123")
        result = await sql_user_repo.get_by_messenger_id("tg_123")

        assert result is not None
        assert result.id == user.id
        assert result.messenger_id == "tg_123"

    async def test_returns_none_for_nonexistent_messenger_id(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
    ) -> None:
        result = await sql_user_repo.get_by_messenger_id("nonexistent_id")

        assert result is None


class TestSqlAlchemyUserRepositoryUpdateChanges:
    async def test_updates_fields(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(first_name="Old")
        result = await sql_user_repo.update_changes(user.id, {"first_name": "New"})

        assert result is not None
        assert result.first_name == "New"

    async def test_updates_multiple_fields(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        result = await sql_user_repo.update_changes(
            user.id,
            {"first_name": "Updated", "last_name": "Name", "language_code": "ru"},
        )

        assert result is not None
        assert result.first_name == "Updated"
        assert result.last_name == "Name"
        assert result.language_code == "ru"

    async def test_returns_none_for_nonexistent_pk(
        self,
        sql_user_repo: repos.SqlAlchemyUserRepository,
    ) -> None:
        result = await sql_user_repo.update_changes(uuid.uuid4(), {"first_name": "X"})
        assert result is None
