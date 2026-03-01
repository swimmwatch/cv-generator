from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.exceptions import TelegramNetworkError
from aiogram.exceptions import TelegramRetryAfter
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from apps.worker.app import broker
from infra.logger.utils import get_logger

logger = get_logger(__name__)


@broker.task()
@inject
async def send_tg_bot_message(
    tg_id: int,
    message: str,
    protect_content: bool | None = None,
    disable_web_page_preview: bool = False,
    disable_notification: bool = False,
    timeout: float | None = None,
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
