import uuid
from decimal import Decimal

from core import dal
from core import models
from tests.factories import UserFactory


class TestUserAsyncDALDeductBalance:
    async def test_deducts_balance(
        self,
        sql_user_dal: dal.UserAsyncDAL,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("10"))

        result = await sql_user_dal.deduct_balance(user_id=user.id, amount=Decimal("3"))

        assert result == Decimal("7")

    async def test_deducts_exact_balance(
        self,
        sql_user_dal: dal.UserAsyncDAL,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("5"))

        result = await sql_user_dal.deduct_balance(user_id=user.id, amount=Decimal("5"))

        assert result == Decimal("0")

    async def test_returns_none_when_insufficient_balance(
        self,
        sql_user_dal: dal.UserAsyncDAL,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("2"))

        result = await sql_user_dal.deduct_balance(user_id=user.id, amount=Decimal("5"))

        assert result is None

    async def test_returns_none_for_nonexistent_user(
        self,
        sql_user_dal: dal.UserAsyncDAL,
    ) -> None:
        result = await sql_user_dal.deduct_balance(user_id=uuid.uuid4(), amount=Decimal("1"))

        assert result is None

    async def test_does_not_modify_balance_when_insufficient(
        self,
        sql_user_dal: dal.UserAsyncDAL,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("3"))

        await sql_user_dal.deduct_balance(user_id=user.id, amount=Decimal("5"))

        result = await sql_user_dal.deduct_balance(user_id=user.id, amount=Decimal("3"))
        assert result == Decimal("0")


class TestUserAsyncDALTopupBalance:
    async def test_adds_to_balance(
        self,
        sql_user_dal: dal.UserAsyncDAL,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("10"))

        result = await sql_user_dal.topup_balance(user_id=user.id, amount=Decimal("50"))

        assert result == Decimal("60")

    async def test_adds_to_zero_balance(
        self,
        sql_user_dal: dal.UserAsyncDAL,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("0"))

        result = await sql_user_dal.topup_balance(user_id=user.id, amount=Decimal("100"))

        assert result == Decimal("100")

    async def test_returns_none_for_nonexistent_user(
        self,
        sql_user_dal: dal.UserAsyncDAL,
    ) -> None:
        result = await sql_user_dal.topup_balance(user_id=uuid.uuid4(), amount=Decimal("50"))

        assert result is None
