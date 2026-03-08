import typing

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from dependency_injector.wiring import Closing
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import services
from infra.logger.utils import get_logger
from utils.telegram.types import MiddlewareType
from utils.transactions.manager import AsyncTransactionManager

logger = get_logger(__name__)


class UpdateOrCreateUserMiddleware(BaseMiddleware):
    @inject
    async def __call__(
        self,
        handler: MiddlewareType,
        event: TelegramObject,
        data: dict[str, typing.Any],
        transaction_manager: AsyncTransactionManager = Closing[Provide["async_transaction_manager_scoped"]],
        user_service: services.UserService = Closing[Provide["user_service"]],
    ) -> typing.Any:
        tg_user = event.message.from_user  # type: ignore[attr-defined]
        if tg_user is None:
            logger.info("Cannot obtain tg_user from event. Skipping user update or create.")
            return await handler(event, data)

        async with transaction_manager:
            user, _ = await user_service.update_or_create_by_tg(tg_user)
            data["user"] = user

        return await handler(event, data)
