import typing
from types import TracebackType

from sqlalchemy import orm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSessionTransaction
from sqlalchemy.orm import SessionTransaction

from infra.logger.utils import get_logger
from utils.transactions.manager import BaseAsyncTransactionManager
from utils.transactions.manager import BaseTransactionManager

logger = get_logger(__name__)


class SqlAlchemyTransactionManager(BaseTransactionManager):
    def __init__(self, session: orm.Session) -> None:
        self._session = session
        self._transaction: SessionTransaction | None = None

    def __enter__(self) -> typing.Self:
        if self._transaction is None:
            self._transaction = self._session.begin(True)
            self._transaction.__enter__()
            logger.debug("SQL transaction was started")

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._transaction is not None and self._transaction.is_active:
            if exc_type is not None:
                self._transaction.rollback()
                logger.debug("SQL transaction was rolled back")

            self._transaction.__exit__(exc_type, exc_val, exc_tb)
            logger.debug("SQL transaction was ended")


class AsyncSqlAlchemyTransactionManager(BaseAsyncTransactionManager):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._transaction: AsyncSessionTransaction | None = None

    async def __aenter__(self) -> typing.Self:
        if self._transaction is None:
            self._transaction = self._session.begin_nested()
            await self._transaction.__aenter__()
            logger.debug("SQL transaction was started")

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._transaction is not None and self._transaction.is_active:
            if exc_type is not None:
                await self._transaction.rollback()
                logger.debug("SQL transaction was rolled back")

            await self._transaction.__aexit__(exc_type, exc_val, exc_tb)
            logger.debug("SQL transaction was ended")
