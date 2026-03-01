from polyfactory.fields import Use
from polyfactory.pytest_plugin import register_fixture

from core import models

from .base import BaseSQLAFactory


@register_fixture
class UserFactory(BaseSQLAFactory[models.User]):
    __model__ = models.User

    messenger_id = Use(lambda: str(BaseSQLAFactory.__faker__.uuid4()))
    username = Use(lambda: BaseSQLAFactory.__faker__.user_name() or "testuser")
    first_name = Use(lambda: BaseSQLAFactory.__faker__.first_name())
    last_name = Use(lambda: BaseSQLAFactory.__faker__.last_name())
    is_staff = False
    is_superuser = False
