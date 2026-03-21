from polyfactory.fields import Ignore
from polyfactory.fields import Use
from polyfactory.pytest_plugin import register_fixture

from core import models

from .base import BaseSQLAFactory


@register_fixture
class JobFactory(BaseSQLAFactory[models.Job]):
    __model__ = models.Job

    title = Use(lambda: BaseSQLAFactory.__faker__.job())
    url = Use(lambda: BaseSQLAFactory.__faker__.url())
    normalized_url = Use(lambda: BaseSQLAFactory.__faker__.domain_name())
    metadata_: dict = Use(lambda: {})  # type: ignore[assignment]
    user = Ignore()
    generated_cvs = Ignore()
