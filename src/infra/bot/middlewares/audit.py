import enum
import typing
import uuid

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.types import Update
from aiogram.types import User as TelegramUser

from infra.logger.utils import get_logger
from utils.telegram.types import MiddlewareType

logger = get_logger(__name__)


class MediaType(enum.StrEnum):
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"


class LoggerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: MiddlewareType,
        event: TelegramObject,
        data: dict[str, typing.Any],
    ) -> typing.Any:
        if isinstance(event, Update):
            await audit_log(event, data)

        return await handler(event, data)


async def audit_log(update: Update, data: dict[str, typing.Any]) -> None:
    structlog.contextvars.clear_contextvars()

    user = data.get("user")
    request_id = data.get("request_id")
    tg_user: TelegramUser | None = None
    if update.message and update.message.from_user:
        tg_user = update.message.from_user
    elif update.callback_query and update.callback_query.from_user:
        tg_user = update.callback_query.from_user

    bind_data: dict[str, str] = {}
    if user is not None and getattr(user, "id", None) is not None:
        bind_data["user_id"] = str(user.id)
    if tg_user is not None:
        bind_data["tg_id"] = str(tg_user.id)
    if request_id is not None:
        bind_data["request_id"] = request_id

    if bind_data:
        structlog.contextvars.bind_contextvars(**bind_data)

    if update.message:
        message = update.message
        message_id = message.message_id
        log = logger.bind(message_id=message_id)

        if message.reply_to_message:
            log.info(
                "Received reply message.",
                reply_to_message_id=message.reply_to_message.message_id,
            )

        media_message = "Received media from message."

        command = None
        if message.text and message.entities:
            for entity in message.entities:
                if str(entity.type) == "bot_command":
                    command = entity.extract_from(message.text)
                    break

        media_type = None
        file_unique_id = None

        if command:
            log.info("Executed command from message.", command=command)
        elif message.text:
            log.info("Received text from message.", text=message.text)
        elif message.photo:
            media_type = MediaType.PHOTO.value
            file_unique_id = message.photo[-1].file_unique_id
        elif message.video:
            media_type = MediaType.VIDEO.value
            file_unique_id = message.video.file_unique_id
        elif message.document:
            media_type = MediaType.DOCUMENT.value
            file_unique_id = message.document.file_unique_id
        elif message.audio:
            media_type = MediaType.AUDIO.value
            file_unique_id = message.audio.file_unique_id

        if media_type:
            log.info(
                media_message,
                media_type=media_type,
                file_unique_id=file_unique_id,
            )

    elif update.callback_query:
        logger.info(
            "Received callback query update.",
            data=update.callback_query.data,
        )


class RequestIdMiddleware(BaseMiddleware):
    """Middleware to ensure each request has a unique ID for tracing."""

    async def __call__(
        self,
        handler: MiddlewareType,
        event: TelegramObject,
        data: dict[str, typing.Any],
    ) -> typing.Any:
        if "request_id" not in data:
            request_id = str(uuid.uuid4())
            logger.debug(f"Assigned new request ID: {request_id}")
        else:
            request_id = data["request_id"]
            logger.debug(f"Request already has ID: {request_id}")

        data["request_id"] = request_id
        return await handler(event, data)
