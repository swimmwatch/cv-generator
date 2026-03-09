import uuid

from core import domains
from utils.dto import BaseDTO
from utils.dto import TimedMixinDTO


class ResumeCreateDTO(BaseDTO):
    user_id: uuid.UUID
    title: str | None = None
    object_name: str
    file_name: str
    status: domains.ResumeProcessingStatus = domains.ResumeProcessingStatus.PENDING


class ResumeOutDTO(BaseDTO, TimedMixinDTO):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str | None = None
    object_name: str
    file_name: str
    status: domains.ResumeProcessingStatus
