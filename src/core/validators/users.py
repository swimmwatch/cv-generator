import typing

from core.repos import UserRepository
from utils.forms.fields import UniqueFieldError
from utils.forms.validators import BaseValidator


class UserValidation:
    REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


class UsernameRegexValidation:
    MESSAGE = "Invalid email format."


class PasswordRegexValidation:
    REGEX = r"^(?=.*[A-Za-z])(?=.*\d).{8,}$"
    MESSAGE = "Password must be at least 8 characters and contain letters and digits."


class UniqueUserEmailValidator(BaseValidator):
    def __init__(self, repo: UserRepository):
        self._repo = repo

    async def __call__(self, field: str, value: typing.Any):
        exists = await self._repo.email_exists(value)  # type: ignore[attr-defined]
        if exists:
            raise UniqueFieldError(field=field)
