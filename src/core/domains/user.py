import typing
import uuid

MessengerID: typing.TypeAlias = str
UserID: typing.TypeAlias = uuid.UUID


class TelegramUserLike(typing.Protocol):
    id: int
    first_name: str
    last_name: str | None
    username: str | None
    language_code: str | None
