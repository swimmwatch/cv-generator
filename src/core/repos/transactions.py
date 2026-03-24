import typing
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core import dal
from core import dto
from core.domains.transaction import TransactionStatus


class TransactionRepository(typing.Protocol):
    async def create_one(self, data: dto.TransactionCreateDTO) -> dto.TransactionOutDTO:
        pass

    async def get_by_pk(self, pk: uuid.UUID) -> dto.TransactionOutDTO | None:
        pass

    async def update_status(
        self,
        pk: uuid.UUID,
        status: TransactionStatus,
        telegram_payment_id: str | None = None,
    ) -> dto.TransactionOutDTO | None:
        pass


class SqlAlchemyTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._dal = dal.TransactionAsyncDAL(session)

    async def create_one(self, data: dto.TransactionCreateDTO) -> dto.TransactionOutDTO:
        instance = await self._dal.create_one(
            user_id=data.user_id,
            credits_amount=data.credits_amount,
            stars_amount=data.stars_amount,
            status=data.status,
        )
        return dto.TransactionOutDTO.from_model(instance)

    async def get_by_pk(self, pk: uuid.UUID) -> dto.TransactionOutDTO | None:
        instance = await self._dal.filter(id=pk).first()
        if not instance:
            return None
        return dto.TransactionOutDTO.from_model(instance)

    async def update_status(
        self,
        pk: uuid.UUID,
        status: TransactionStatus,
        telegram_payment_id: str | None = None,
    ) -> dto.TransactionOutDTO | None:
        instance = await self._dal.filter(id=pk).first()
        if not instance:
            return None

        changes: dict[str, typing.Any] = {"status": status}
        if telegram_payment_id is not None:
            changes["telegram_payment_id"] = telegram_payment_id

        await self._dal.update_instance(instance, **changes)
        await self._session.refresh(instance)
        return dto.TransactionOutDTO.from_model(instance)
