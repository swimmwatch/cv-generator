from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import domains
from core import dto
from infra.bot.template import TelegramTemplate
from utils.lang import _

from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)


@router.message(Command("balance"))
@inject
async def balance(
    message: Message,
    user: dto.UserOutDTO,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    lang = get_lang(message.from_user)
    costs = [
        (_("Chat message"), int(domains.CreditAction.CHAT_MESSAGE)),
        (_("Resume upload"), int(domains.CreditAction.RESUME_UPLOAD)),
        (_("Job posting"), int(domains.CreditAction.JOB_POSTING)),
        (_("CV generation"), int(domains.CreditAction.CV_GENERATION)),
    ]
    text = telegram_template.render(
        "balance/info.html",
        lang,
        balance=user.balance,
        costs=costs,
    )
    await send_response(message, text)
