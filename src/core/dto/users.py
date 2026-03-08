from core import domains
from utils.dto import BaseDTO
from utils.dto import TimedMixinDTO


class BaseUserDTO(BaseDTO):
    messenger_id: domains.MessengerID
    username: str | None = None
    first_name: str
    last_name: str | None = None
    password_hash: str | None = None
    is_superuser: bool
    is_staff: bool
    language_code: str | None = None


class UserCreateDTO(BaseUserDTO):
    pass


class UserAdminCreateDTO(BaseDTO):
    messenger_id: domains.MessengerID
    username: str | None = None
    password: str
    first_name: str
    last_name: str | None = None


class UserOutDTO(
    BaseUserDTO,
    TimedMixinDTO,
):
    id: domains.UserID
