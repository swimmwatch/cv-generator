import typing

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from infra.db.client import AsyncDatabase
from infra.db.session_scope import clear_session_scope
from infra.db.session_scope import set_session_scope
from infra.logger.utils import get_logger
from utils.telegram.types import MiddlewareType

logger = get_logger(__name__)


class DBSessionMiddleware(BaseMiddleware):
    def __init__(self, db: AsyncDatabase) -> None:
        super().__init__()
        self._db = db

    async def __call__(
        self,
        handler: MiddlewareType,
        event: TelegramObject,
        data: dict[str, typing.Any],
    ) -> typing.Any:
        scope_key = data.get("request_id")  # Ensure this is set by RequestIdMiddleware
        set_session_scope(scope_key)

        try:
            response = await handler(event, data)
            await self._db.commit_scoped_session()
            return response
        except Exception as err:
            logger.exception(err)

            await self._db.rollback_scoped_session()
            raise
        finally:
            clear_session_scope()
            await self._db.remove_scoped_session()
