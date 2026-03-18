from polyfactory.fields import Ignore
from polyfactory.fields import Use
from polyfactory.pytest_plugin import register_fixture

from core import models

from .base import BaseSQLAFactory


@register_fixture
class GeneratedCVFactory(BaseSQLAFactory[models.GeneratedCV]):
    __model__ = models.GeneratedCV

    object_name = Use(lambda: f"generated_cvs/{BaseSQLAFactory.__faker__.uuid4()}.pdf")
    file_name = Use(lambda: f"cv_{BaseSQLAFactory.__faker__.file_name(extension='pdf')}")
    user = Ignore()
    resume = Ignore()
    job = Ignore()
