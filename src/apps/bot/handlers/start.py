from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from infra.bot.template import TelegramTemplate

from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)


@router.message(Command("start"))
@inject
async def start(
    message: Message,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    user = message.from_user
    lang = get_lang(user)

    response = telegram_template.render(
        "greet.html",
        lang,
        user=user,
    )
    await send_response(message, response)
