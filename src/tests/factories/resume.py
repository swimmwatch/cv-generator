from polyfactory.fields import Ignore
from polyfactory.fields import Use
from polyfactory.pytest_plugin import register_fixture

from core import domains
from core import models

from .base import BaseSQLAFactory


@register_fixture
class ResumeFactory(BaseSQLAFactory[models.Resume]):
    __model__ = models.Resume

    title = Use(lambda: BaseSQLAFactory.__faker__.sentence(nb_words=3))
    object_name = Use(lambda: f"resumes/{BaseSQLAFactory.__faker__.uuid4()}.pdf")
    file_name = Use(lambda: f"{BaseSQLAFactory.__faker__.file_name(extension='pdf')}")
    status = domains.ResumeProcessingStatus.PENDING
    user = Ignore()
    generated_cvs = Ignore()
