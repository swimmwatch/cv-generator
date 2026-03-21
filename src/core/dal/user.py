import uuid

import sqlalchemy as sa

from core import domains
from core import models
from infra.db.utils.dal.async_ import SqlAlchemyAsyncDAL


class UserAsyncDAL(SqlAlchemyAsyncDAL):
    class Meta(SqlAlchemyAsyncDAL.Meta):
        model = models.User

    async def deduct_balance(self, user_id: uuid.UUID, amount: domains.CreditAmount) -> domains.CreditAmount | None:
        new_balance = models.User.balance - amount
        stmt = sa.update(models.User).where(
            models.User.id == user_id,
            models.User.balance >= amount,
        )
        stmt = stmt.values(balance=new_balance).returning(models.User.balance)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def topup_balance(self, user_id: uuid.UUID, amount: domains.CreditAmount) -> domains.CreditAmount | None:
        new_balance = models.User.balance + amount
        stmt = sa.update(models.User).where(models.User.id == user_id)
        stmt = stmt.values(balance=new_balance).returning(models.User.balance)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
