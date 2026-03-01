from typing import TypeVar

from infra.db.base import Model

ModelType = TypeVar("ModelType", bound=Model)
