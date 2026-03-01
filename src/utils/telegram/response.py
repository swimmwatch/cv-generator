"""
Telegram response utilities.
"""

from typing import Union
from typing import cast

import telegram
from telegram import Chat
from telegram import ForceReply
from telegram import InlineKeyboardMarkup
from telegram import ReplyKeyboardMarkup
from telegram import ReplyKeyboardRemove
from telegram import Update
from telegram.ext import ContextTypes

KeyboardType = Union[
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ForceReply,
]


async def send_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    response: str,
    keyboard: KeyboardType | None = None,
) -> None:
    await context.bot.send_message(
        chat_id=_get_chat_id(update),
        disable_web_page_preview=True,
        text=response,
        parse_mode=telegram.constants.ParseMode.HTML,
        reply_markup=keyboard,
    )


def _get_chat_id(update: Update) -> int:
    return cast(Chat, update.effective_chat).id
