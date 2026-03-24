from polyfactory.fields import Ignore
from polyfactory.fields import Use
from polyfactory.pytest_plugin import register_fixture

from core import models
from core.domains.transaction import TransactionStatus

from .base import BaseSQLAFactory


@register_fixture
class TransactionFactory(BaseSQLAFactory[models.Transaction]):
    __model__ = models.Transaction

    credits_amount = Use(lambda: 50)
    stars_amount = Use(lambda: 50)
    status = TransactionStatus.PENDING
    telegram_payment_id = None
    user = Ignore()
