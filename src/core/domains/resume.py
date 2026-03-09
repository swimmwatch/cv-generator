import enum
import uuid

ResumeID = uuid.UUID


class ResumeProcessingStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


ALLOWED_RESUME_EXTENSIONS = (".pdf", ".docx", ".doc")

ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
