import typing
from dataclasses import dataclass


@dataclass(slots=True)
class JobChunk:
    job_id: str
    user_id: str
    section: str
    content: str
    metadata: dict[str, typing.Any]
