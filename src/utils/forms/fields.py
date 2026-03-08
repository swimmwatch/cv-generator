from enum import StrEnum

from utils.errors.base import BaseError


class FieldErrorType(StrEnum):
    UNIQUE_FIELD = "unique_field"
    INVALID_FORMAT = "invalid_format"
    DATA_REQUIRED = "data_required"


class FieldError(BaseError):
    field: str

    def __init__(self, field: str, message: str, type_: str):  # noqa: B042
        self.field = field
        self.message = message
        self.type = type_
        super().__init__(field=field, message=message, type=type_)


class UniqueFieldError(FieldError):
    def __init__(self, field: str):  # noqa: B042
        message = f"The {field.replace('_', ' ')} is already taken."
        super().__init__(field, message, FieldErrorType.UNIQUE_FIELD)


class RegrexFieldError(FieldError):
    def __init__(self, field: str, message: str):  # noqa: B042
        super().__init__(field, message, FieldErrorType.INVALID_FORMAT)


class DataRequiredFieldError(FieldError):
    def __init__(self, field: str):  # noqa: B042
        message = f"{field.replace('_', ' ').capitalize()} is required."
        super().__init__(field, message, FieldErrorType.DATA_REQUIRED)
