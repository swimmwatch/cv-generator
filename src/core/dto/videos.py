from datetime import datetime
from uuid import UUID

from core import domains
from utils.dto import BaseDTO


class VideoUpsertDTO(BaseDTO):
    source_type: str
    source_pk: str
    title: str | None = None
    description: str | None = None
    published_at: datetime | None = None


class VideoOutDTO(BaseDTO):
    id: UUID
    source_type: str
    source_pk: str
    title: str | None
    description: str | None
    processing_status: domains.VideoProcessingStatus
    reject_reason_codes: list[str]
