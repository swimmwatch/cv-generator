import uuid

from core import domains
from core.domains.transaction import TransactionStatus
from utils.dto import BaseDTO
from utils.dto import TimedMixinDTO


class TransactionCreateDTO(BaseDTO):
    user_id: uuid.UUID
    credits_amount: domains.CreditAmount
    stars_amount: int
    status: TransactionStatus = TransactionStatus.PENDING


class TransactionOutDTO(BaseDTO, TimedMixinDTO):
    id: uuid.UUID
    user_id: uuid.UUID
    credits_amount: domains.CreditAmount
    stars_amount: int
    status: TransactionStatus
    telegram_payment_id: str | None = None
