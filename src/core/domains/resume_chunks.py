import typing
from dataclasses import dataclass


@dataclass(slots=True)
class ResumeChunk:
    resume_id: str
    user_id: str
    section: str
    content: str
    metadata: dict[str, typing.Any]
