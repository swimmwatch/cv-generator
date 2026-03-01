import typing
from types import TracebackType

from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorClientSession

from infra.logger.utils import get_logger
from utils.transactions.manager import BaseAsyncTransactionManager

logger = get_logger(__name__)


class AsyncMongoTransactionManager(BaseAsyncTransactionManager):
    def __init__(self, client: AsyncIOMotorClient) -> None:
        self._client = client
        self._session: AsyncIOMotorClientSession | None = None

    @property
    def session(self) -> AsyncIOMotorClientSession | None:
        return self._session

    async def __aenter__(self) -> typing.Self:
        self._session = await self._client.start_session()
        self._session.start_transaction()
        logger.debug("MongoDB transaction was started")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session is None:
            return

        try:
            if exc_type is not None:
                await self._session.abort_transaction()
                logger.debug("MongoDB transaction was rolled back")
            else:
                await self._session.commit_transaction()
                logger.debug("MongoDB transaction was committed")
        finally:
            await self._session.end_session()
            self._session = None
