import uuid

from core import domains
from core import dto
from core import repos
from core.domains.transaction import TransactionStatus
from infra.logger.utils import get_logger

logger = get_logger(__name__)


class TransactionService:
    def __init__(
        self,
        transaction_repo: repos.TransactionRepository,
        user_repo: repos.UserRepository,
    ) -> None:
        self._transaction_repo = transaction_repo
        self._user_repo = user_repo

    async def create_pending(
        self,
        user_id: domains.UserID,
        credits_amount: domains.CreditAmount,
        stars_amount: int,
    ) -> dto.TransactionOutDTO:
        data = dto.TransactionCreateDTO(
            user_id=user_id,
            credits_amount=credits_amount,
            stars_amount=stars_amount,
            status=TransactionStatus.PENDING,
        )
        transaction = await self._transaction_repo.create_one(data)
        logger.info(
            "Transaction created",
            transaction_id=str(transaction.id),
            user_id=str(user_id),
        )
        return transaction

    async def confirm(self, transaction_id: uuid.UUID) -> dto.TransactionOutDTO | None:
        return await self._transaction_repo.update_status(
            pk=transaction_id,
            status=TransactionStatus.CONFIRMED,
        )

    async def complete(
        self,
        transaction_id: uuid.UUID,
        telegram_payment_id: str,
    ) -> dto.TransactionOutDTO | None:
        transaction = await self._transaction_repo.get_by_pk(transaction_id)
        if not transaction:
            logger.warning("Transaction not found", transaction_id=str(transaction_id))
            return None

        new_balance = await self._user_repo.topup_balance(
            user_id=transaction.user_id,
            amount=transaction.credits_amount,
        )

        updated = await self._transaction_repo.update_status(
            pk=transaction_id,
            status=TransactionStatus.COMPLETED,
            telegram_payment_id=telegram_payment_id,
        )

        logger.info(
            "Transaction completed",
            transaction_id=str(transaction_id),
            new_balance=str(new_balance),
        )
        return updated

    async def fail(self, transaction_id: uuid.UUID) -> dto.TransactionOutDTO | None:
        return await self._transaction_repo.update_status(
            pk=transaction_id,
            status=TransactionStatus.FAILED,
        )
