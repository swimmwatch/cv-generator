import typing
from copy import deepcopy
from string import Template

from fastapi.encoders import jsonable_encoder


class BaseError(Exception):
    type: str = ""
    message: str = ""
    message_template: str = ""
    data: dict | None = None

    def __init__(self, **kwargs):  # noqa: B042
        if self.data is None:
            self.data = deepcopy(kwargs)

        if not self.message:
            self.message = Template(self.message_template).substitute(kwargs)

        super().__init__(self.message)

    def to_json(self) -> dict[str, typing.Any]:
        data = {"data": self.data.get("data", self.data)}  # type: ignore[union-attr]
        data = jsonable_encoder(data)

        return {
            "type": self.type,
            "message": self.message,
            **data,
        }
