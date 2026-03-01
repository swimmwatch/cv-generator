from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from infra.bot.template import TelegramTemplate
from utils.lang import _

from .utils import send_response

router = Router(name=__name__)


@router.message(Command("start"))
@inject
async def start(
    message: Message,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    user = message.from_user
    lang = getattr(user, "language_code", None) if user else None

    response = telegram_template.render(
        "greet.html",
        lang,
        user=user,
    )
    await send_response(message, response)


@router.message()
@inject
async def fallback(
    message: Message,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    user = message.from_user
    lang = getattr(user, "language_code", None) if user else None

    text = _("Ops! I don't know what I can do.")
    text = telegram_template.render_error(text, lang)

    await send_response(message, text)
