import typing
import uuid

from core import domains
from utils.dto import BaseDTO
from utils.dto import TimedMixinDTO


class JobCreateDTO(BaseDTO):
    user_id: uuid.UUID
    title: str
    url: str
    metadata_: typing.Any = None


class JobOutDTO(BaseDTO, TimedMixinDTO):
    id: domains.JobID
    user_id: uuid.UUID
    title: str
    url: str
    metadata_: typing.Any = None
