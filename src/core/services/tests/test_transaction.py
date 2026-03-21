import uuid
from decimal import Decimal

from core import models
from core import services
from core.domains.transaction import TransactionStatus
from tests.factories import UserFactory


class TestTransactionServiceCreatePending:
    async def test_creates_pending_transaction(
        self,
        transaction_service: services.TransactionService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()

        result = await transaction_service.create_pending(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )

        assert result.user_id == user.id
        assert result.credits_amount == Decimal("50")
        assert result.stars_amount == 50
        assert result.status == TransactionStatus.PENDING
        assert result.id is not None


class TestTransactionServiceConfirm:
    async def test_confirms_transaction(
        self,
        transaction_service: services.TransactionService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        tx = await transaction_service.create_pending(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )

        result = await transaction_service.confirm(tx.id)

        assert result is not None
        assert result.status == TransactionStatus.CONFIRMED

    async def test_returns_none_for_nonexistent_transaction(
        self,
        transaction_service: services.TransactionService,
    ) -> None:
        result = await transaction_service.confirm(uuid.uuid4())

        assert result is None


class TestTransactionServiceComplete:
    async def test_completes_transaction_and_topups_balance(
        self,
        transaction_service: services.TransactionService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("10"))
        tx = await transaction_service.create_pending(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )

        result = await transaction_service.complete(
            transaction_id=tx.id,
            telegram_payment_id="tg_charge_abc",
        )

        assert result is not None
        assert result.status == TransactionStatus.COMPLETED
        assert result.telegram_payment_id == "tg_charge_abc"

    async def test_returns_none_for_nonexistent_transaction(
        self,
        transaction_service: services.TransactionService,
    ) -> None:
        result = await transaction_service.complete(
            transaction_id=uuid.uuid4(),
            telegram_payment_id="tg_charge_xyz",
        )

        assert result is None

    async def test_balance_reflects_topup(
        self,
        transaction_service: services.TransactionService,
        user_factory: UserFactory,
        sql_user_repo,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("10"))
        tx = await transaction_service.create_pending(
            user_id=user.id,
            credits_amount=Decimal("100"),
            stars_amount=90,
        )

        await transaction_service.complete(
            transaction_id=tx.id,
            telegram_payment_id="tg_charge_check",
        )

        updated_user = await sql_user_repo.get_by_pk(user.id)
        assert updated_user.balance == Decimal("110")


class TestTransactionServiceFail:
    async def test_fails_transaction(
        self,
        transaction_service: services.TransactionService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        tx = await transaction_service.create_pending(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )

        result = await transaction_service.fail(tx.id)

        assert result is not None
        assert result.status == TransactionStatus.FAILED

    async def test_returns_none_for_nonexistent_transaction(
        self,
        transaction_service: services.TransactionService,
    ) -> None:
        result = await transaction_service.fail(uuid.uuid4())

        assert result is None

    async def test_does_not_affect_user_balance(
        self,
        transaction_service: services.TransactionService,
        user_factory: UserFactory,
        sql_user_repo,
    ) -> None:
        user: models.User = await user_factory.create_async(balance=Decimal("10"))
        tx = await transaction_service.create_pending(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )

        await transaction_service.fail(tx.id)

        updated_user = await sql_user_repo.get_by_pk(user.id)
        assert updated_user.balance == Decimal("10")
