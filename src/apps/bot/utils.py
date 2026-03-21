import typing

from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import ReplyMarkupUnion


def get_lang(user: typing.Any) -> str | None:
    return getattr(user, "language_code", None) if user else None


async def send_response(
    message: Message,
    response: str,
    keyboard: ReplyMarkupUnion | None = None,
) -> None:
    if message.chat is None or message.bot is None:
        return

    await message.bot.send_message(
        chat_id=message.chat.id,
        disable_web_page_preview=True,
        text=response,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )
