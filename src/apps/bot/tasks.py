from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.exceptions import TelegramNetworkError
from aiogram.exceptions import TelegramRetryAfter
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from taskiq import Context
from taskiq import TaskiqDepends

from apps.worker.app import broker
from core import services
from core.domains.user import UserID
from infra.bot.template import TelegramTemplate
from infra.logger.utils import get_logger
from utils.extractors import TextExtractorFactory
from utils.storages.impl.base import AsyncStorage

logger = get_logger(__name__)

_taskiq_context: Context = TaskiqDepends()  # type: ignore[assignment]


@broker.task()
@inject
async def send_tg_bot_message(
    tg_id: int,
    message: str,
    protect_content: bool | None = None,
    disable_web_page_preview: bool = False,
    disable_notification: bool = False,
    timeout: int | None = None,
    parse_mode: str | None = "HTML",
    tg_bot: Bot = Provide["tg_bot_client"],
) -> None:
    try:
        await tg_bot.send_message(
            tg_id,
            message,
            protect_content=protect_content,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            parse_mode=parse_mode,
            request_timeout=timeout,
        )
    except TelegramNetworkError as err:
        logger.error("Cannot send message due to network error.")
        logger.exception(err)
        raise err
    except TelegramBadRequest as err:
        logger.error("Cannot send message due to bad request error")
        logger.exception(err)
        return
    except TelegramForbiddenError as err:
        logger.warning("Cannot send message due to forbidden error.")
        logger.exception(err)
        return
    except TelegramRetryAfter as err:
        logger.warning("Cannot send message due to flood error.")
        logger.exception(err)
        raise err
    except Exception as err:
        logger.exception(err)
        raise err

    logger.info("Message was sent.", tg_id=tg_id)
    logger.debug("Message content:\n%s", message)


@broker.task(retry_on_error=True, max_retries=3)
@inject
async def process_resume(
    user_id: str,
    object_name: str,
    file_name: str,
    async_storage: AsyncStorage = Provide["s3_async_storage"],
    telegram_template: TelegramTemplate = Provide["telegram_template"],
    user_service: services.UserService = Provide["user_service"],
    context: Context = _taskiq_context,
) -> None:
    log = logger.bind(user_id=user_id, object_name=object_name, file_name=file_name)
    log.info("Starting resume processing.")

    user = await user_service.get_current_user(UserID(user_id))
    if user is None:
        log.error("User not found.")
        return

    tg_id = int(user.messenger_id)
    log = log.bind(tg_id=tg_id)

    retries = int(context.message.labels.get("_retries", 0))
    max_retries = int(context.message.labels.get("max_retries", 3))

    try:
        file_data = await async_storage.get_bytes(object_name)
        log.info("Resume file downloaded from storage.")

        extractor = TextExtractorFactory.get(file_name)
        markdown_text = extractor.extract(file_data)
        log.info("Resume text extracted.", length=len(markdown_text))
    except Exception:
        log.exception("Resume processing failed.", attempt=retries + 1)

        if retries + 1 >= max_retries:
            text = telegram_template.render("resume/failed.html", None)
            await send_tg_bot_message.kiq(tg_id, text)

        raise
