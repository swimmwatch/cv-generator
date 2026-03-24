import typing

from sqlalchemy.ext.asyncio import AsyncSession

from core import dal
from core import domains
from core import dto
from core.dto import UserOutDTO


class UserRepository(typing.Protocol):
    async def create_one(self, data: dto.UserCreateDTO) -> dto.UserOutDTO:
        pass

    async def get_by_username(self, username: str) -> dto.UserOutDTO | None:
        pass

    async def get_by_messenger_id(self, messenger_id: str) -> dto.UserOutDTO | None:
        pass

    async def get_by_pk(self, pk: domains.UserID) -> dto.UserOutDTO | None:
        pass

    async def update_changes(
        self,
        pk: domains.UserID,
        data: dict[str, typing.Any],
    ) -> UserOutDTO | None:
        pass

    async def deduct_balance(
        self, user_id: domains.UserID, amount: domains.CreditAmount
    ) -> domains.CreditAmount | None:
        pass

    async def topup_balance(self, user_id: domains.UserID, amount: domains.CreditAmount) -> domains.CreditAmount | None:
        pass


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._user_dal = dal.UserAsyncDAL(session)

    async def create_one(self, data: dto.UserCreateDTO) -> dto.UserOutDTO:
        user = await self._user_dal.create_one(
            messenger_id=data.messenger_id,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            password_hash=data.password_hash,
            is_superuser=data.is_superuser,
            is_staff=data.is_staff,
            language_code=data.language_code,
        )
        return dto.UserOutDTO.from_model(user)

    async def get_by_username(self, username: str) -> dto.UserOutDTO | None:
        user = await self._user_dal.filter(username=username).first()
        if not user:
            return None

        return dto.UserOutDTO.from_model(user)

    async def get_by_messenger_id(self, messenger_id: str) -> dto.UserOutDTO | None:
        user = await self._user_dal.filter(messenger_id=messenger_id).first()
        if not user:
            return None

        return dto.UserOutDTO.from_model(user)

    async def get_by_pk(self, pk: domains.UserID) -> dto.UserOutDTO | None:
        user = await self._user_dal.filter(id=pk).first()
        if not user:
            return None

        return dto.UserOutDTO.from_model(user)

    async def update_changes(
        self,
        pk: domains.UserID,
        data: dict[str, typing.Any],
    ) -> UserOutDTO | None:
        rows_count = await self._user_dal.filter(id=pk).update(**data)
        if rows_count == 0:
            return None

        return await self.get_by_pk(pk)

    async def deduct_balance(
        self, user_id: domains.UserID, amount: domains.CreditAmount
    ) -> domains.CreditAmount | None:
        return await self._user_dal.deduct_balance(user_id=user_id, amount=amount)

    async def topup_balance(self, user_id: domains.UserID, amount: domains.CreditAmount) -> domains.CreditAmount | None:
        return await self._user_dal.topup_balance(user_id=user_id, amount=amount)
