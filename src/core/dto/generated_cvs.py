import uuid

from utils.dto import BaseDTO
from utils.dto import TimedMixinDTO


class GeneratedCVCreateDTO(BaseDTO):
    user_id: uuid.UUID
    resume_id: uuid.UUID
    job_id: uuid.UUID
    object_name: str
    file_name: str


class GeneratedCVOutDTO(BaseDTO, TimedMixinDTO):
    id: uuid.UUID
    user_id: uuid.UUID
    resume_id: uuid.UUID
    job_id: uuid.UUID
    object_name: str
    file_name: str
