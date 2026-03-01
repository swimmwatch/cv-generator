import typing

from telegram.ext import Application
from telegram.ext import CallbackContext
from telegram.ext import ExtBot


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    """Custom class for context."""

    def __init__(
        self,
        application: Application,
        chat_id: int | None = None,
        user_id: int | None = None,
    ):
        super().__init__(application=application, chat_id=chat_id, user_id=user_id)
        self._kwargs: dict[str, typing.Any] = {}

    @property
    def kwargs(self) -> dict:
        return self._kwargs

    @kwargs.setter
    def kwargs(self, value: dict) -> None:
        self._kwargs = value
