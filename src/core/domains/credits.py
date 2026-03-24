import enum
import typing
from decimal import Decimal

CreditAmount: typing.TypeAlias = Decimal

DEFAULT_BALANCE: CreditAmount = CreditAmount("50")


class CreditAction(enum.IntEnum):
    CHAT_MESSAGE = 1
    RESUME_UPLOAD = 2
    JOB_POSTING = 2
    CV_GENERATION = 5


class CreditPack(enum.Enum):
    STARTER = (10, 10)
    SMALL = (50, 50)
    MEDIUM = (100, 90)
    LARGE = (500, 400)

    def __init__(self, credits: int, stars_price: int) -> None:
        self.credits = credits
        self.stars_price = stars_price
