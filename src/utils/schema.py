import typing
from datetime import datetime

from pydantic import BaseModel

from utils.dto import BaseDTO


class BaseSchema(BaseModel):
    @classmethod
    def from_dto(cls, dto: BaseDTO) -> typing.Self:
        return cls.model_validate(dto.model_dump())

    @classmethod
    def from_raw(cls, data: dict) -> typing.Self:
        return cls.model_validate(data)


class TimedSchemaMixin:
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    is_active: bool
