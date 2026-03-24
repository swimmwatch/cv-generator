import uuid
from decimal import Decimal

from core import domains
from core import models
from core import services
from tests.factories import UserFactory


class TestUserServiceDeductCredits:
    async def test_deducts_credits(
        self,
        user_service: services.UserService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("10"))

        result = await user_service.deduct_credits(
            user_id=user.id,
            action=domains.CreditAction.CHAT_MESSAGE,
        )

        assert result is True

    async def test_returns_false_when_insufficient(
        self,
        user_service: services.UserService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("1"))

        result = await user_service.deduct_credits(
            user_id=user.id,
            action=domains.CreditAction.CV_GENERATION,
        )

        assert result is False

    async def test_returns_false_for_nonexistent_user(
        self,
        user_service: services.UserService,
    ) -> None:
        result = await user_service.deduct_credits(
            user_id=uuid.uuid4(),
            action=domains.CreditAction.CHAT_MESSAGE,
        )

        assert result is False

    async def test_deducts_exact_cost(
        self,
        user_service: services.UserService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("5"))

        result = await user_service.deduct_credits(
            user_id=user.id,
            action=domains.CreditAction.CV_GENERATION,
        )

        assert result is True

    async def test_fails_when_balance_less_than_cost(
        self,
        user_service: services.UserService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("4"))

        result = await user_service.deduct_credits(
            user_id=user.id,
            action=domains.CreditAction.CV_GENERATION,
        )

        assert result is False


class TestUserServiceTopupCredits:
    async def test_topups_balance(
        self,
        user_service: services.UserService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("10"))

        result = await user_service.topup_credits(
            user_id=user.id,
            amount=Decimal("50"),
        )

        assert result == Decimal("60")

    async def test_returns_none_for_nonexistent_user(
        self,
        user_service: services.UserService,
    ) -> None:
        result = await user_service.topup_credits(
            user_id=uuid.uuid4(),
            amount=Decimal("50"),
        )

        assert result is None
