import typing

from aiogram.types import TelegramObject

MiddlewareType: typing.TypeAlias = typing.Callable[
    [TelegramObject, dict[str, typing.Any]],
    typing.Awaitable[typing.Any],
]
