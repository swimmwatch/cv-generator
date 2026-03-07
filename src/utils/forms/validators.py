import abc
import re
import typing

from .fields import DataRequiredFieldError
from .fields import RegrexFieldError


class BaseValidator(abc.ABC):
    @abc.abstractmethod
    async def __call__(self, field: str, value: typing.Any):
        raise NotImplementedError()


class RegexValidator(BaseValidator):
    def __init__(self, pattern: str, message: str):
        self.pattern = pattern
        self.message = message

    async def __call__(self, field: str, value: typing.Any):
        value = typing.cast(str, value)
        if not re.match(self.pattern, value):
            raise RegrexFieldError(field, message=self.message)


class DataRequiredValidator(BaseValidator):
    async def __call__(self, field: str, value: typing.Any):
        value = typing.cast(str, value)
        if not value.strip():
            raise DataRequiredFieldError(field)
