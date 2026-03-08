from utils.errors.base import BaseError

from .fields import FieldError


class BaseValidationError(BaseError):
    def __init__(self, errors: list[FieldError]):  # noqa: B042
        self.errors = errors
        super().__init__(data=self._group_errors())

    def _group_errors(self) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}

        for err in self.errors:
            grouped.setdefault(err.field, []).append(
                {
                    "type": err.type,
                    "message": err.message,
                }
            )

        return grouped

    def __iter__(self):
        for err in self.errors:
            yield err.field, type(err)
