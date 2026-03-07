import typing

from core.repos import UserRepository
from utils.forms.fields import UniqueFieldError
from utils.forms.validators import BaseValidator


class UniqueUserEmailValidator(BaseValidator):
    def __init__(self, repo: UserRepository):
        self._repo = repo

    async def __call__(self, field: str, value: typing.Any):
        exists = await self._repo.email_exists(value)
        if exists:
            raise UniqueFieldError(field=field)
