from aiogram import Router
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from infra.bot.template import TelegramTemplate
from utils.lang import _

from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)


@router.message()
@inject
async def fallback(
    message: Message,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    user = message.from_user
    lang = get_lang(user)

    text = _("Ops! I don't know what I can do.")
    text = telegram_template.render_error(text, lang)

    await send_response(message, text)
