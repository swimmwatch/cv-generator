import functools
import typing

from telegram import Update
from telegram.ext import ContextTypes


def serve_only_specific_user(user_id: int) -> typing.Callable:
    """
    Decorates Python Telegram Bot handler for serving only specific user messages.
    :param user_id: Telegram user ID
    :return: Decorated handler
    """

    def decorator(handler: typing.Callable) -> typing.Callable:
        @functools.wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> None:
            message = update.message
            if not message:
                return

            from_user = message.from_user
            if not from_user:
                return

            sender_id = from_user.id
            if sender_id == user_id:
                await handler(update, context, *args, **kwargs)

        return wrapper

    return decorator
