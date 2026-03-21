import uuid
from decimal import Decimal

from core import dto
from core import models
from core import repos
from core.domains.transaction import TransactionStatus
from tests.factories import UserFactory


class TestSqlAlchemyTransactionRepositoryCreateOne:
    async def test_creates_transaction(
        self,
        sql_transaction_repo: repos.SqlAlchemyTransactionRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.TransactionCreateDTO(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
            status=TransactionStatus.PENDING,
        )

        result = await sql_transaction_repo.create_one(data)

        assert result.user_id == user.id
        assert result.credits_amount == Decimal("50")
        assert result.stars_amount == 50
        assert result.status == TransactionStatus.PENDING
        assert result.telegram_payment_id is None
        assert result.id is not None

    async def test_creates_transaction_with_confirmed_status(
        self,
        sql_transaction_repo: repos.SqlAlchemyTransactionRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.TransactionCreateDTO(
            user_id=user.id,
            credits_amount=Decimal("100"),
            stars_amount=90,
            status=TransactionStatus.CONFIRMED,
        )

        result = await sql_transaction_repo.create_one(data)

        assert result.status == TransactionStatus.CONFIRMED


class TestSqlAlchemyTransactionRepositoryGetByPk:
    async def test_returns_transaction(
        self,
        sql_transaction_repo: repos.SqlAlchemyTransactionRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.TransactionCreateDTO(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )
        created = await sql_transaction_repo.create_one(data)

        result = await sql_transaction_repo.get_by_pk(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.user_id == user.id

    async def test_returns_none_for_nonexistent_pk(
        self,
        sql_transaction_repo: repos.SqlAlchemyTransactionRepository,
    ) -> None:
        result = await sql_transaction_repo.get_by_pk(uuid.uuid4())

        assert result is None


class TestSqlAlchemyTransactionRepositoryUpdateStatus:
    async def test_updates_status(
        self,
        sql_transaction_repo: repos.SqlAlchemyTransactionRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.TransactionCreateDTO(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )
        created = await sql_transaction_repo.create_one(data)

        result = await sql_transaction_repo.update_status(
            pk=created.id,
            status=TransactionStatus.CONFIRMED,
        )

        assert result is not None
        assert result.status == TransactionStatus.CONFIRMED

    async def test_updates_status_with_payment_id(
        self,
        sql_transaction_repo: repos.SqlAlchemyTransactionRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.TransactionCreateDTO(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )
        created = await sql_transaction_repo.create_one(data)

        result = await sql_transaction_repo.update_status(
            pk=created.id,
            status=TransactionStatus.COMPLETED,
            telegram_payment_id="tg_pay_123",
        )

        assert result is not None
        assert result.status == TransactionStatus.COMPLETED
        assert result.telegram_payment_id == "tg_pay_123"

    async def test_returns_none_for_nonexistent_pk(
        self,
        sql_transaction_repo: repos.SqlAlchemyTransactionRepository,
    ) -> None:
        result = await sql_transaction_repo.update_status(
            pk=uuid.uuid4(),
            status=TransactionStatus.FAILED,
        )

        assert result is None

    async def test_does_not_overwrite_payment_id_when_not_provided(
        self,
        sql_transaction_repo: repos.SqlAlchemyTransactionRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.TransactionCreateDTO(
            user_id=user.id,
            credits_amount=Decimal("50"),
            stars_amount=50,
        )
        created = await sql_transaction_repo.create_one(data)

        await sql_transaction_repo.update_status(
            pk=created.id,
            status=TransactionStatus.COMPLETED,
            telegram_payment_id="tg_pay_456",
        )
        result = await sql_transaction_repo.update_status(
            pk=created.id,
            status=TransactionStatus.REFUNDED,
        )

        assert result is not None
        assert result.status == TransactionStatus.REFUNDED
        assert result.telegram_payment_id == "tg_pay_456"
