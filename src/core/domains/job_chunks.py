import typing
from dataclasses import dataclass

from .job import JobID
from .user import UserID


@dataclass(slots=True)
class JobChunk:
    job_id: str
    user_id: str
    resume_id: str
    section: str
    content: str
    metadata: dict[str, typing.Any]


def chunk_job(
    job_id: JobID,
    user_id: UserID,
    resume_id: str,
    job_text: str,
) -> list[JobChunk]:
    str_job_id = str(job_id)
    str_user_id = str(user_id)
    base_metadata = {
        "job_id": str_job_id,
        "user_id": str_user_id,
        "resume_id": resume_id,
    }
    chunks: list[JobChunk] = []

    chunks.append(
        JobChunk(
            job_id=str_job_id,
            user_id=str_user_id,
            resume_id=resume_id,
            section="full_job",
            content=job_text,
            metadata=base_metadata,
        )
    )

    sections = _split_into_sections(job_text)
    for section_name, section_text in sections.items():
        if section_text.strip():
            chunks.append(
                JobChunk(
                    job_id=str_job_id,
                    user_id=str_user_id,
                    resume_id=resume_id,
                    section=section_name,
                    content=section_text.strip(),
                    metadata={**base_metadata, "section": section_name},
                )
            )

    return chunks


_SECTION_HEADERS = [
    "about",
    "about us",
    "about the role",
    "about the company",
    "description",
    "responsibilities",
    "requirements",
    "qualifications",
    "skills",
    "experience",
    "education",
    "benefits",
    "conditions",
    "what we offer",
    "nice to have",
    "preferred",
    "compensation",
    "salary",
    "location",
]


def _split_into_sections(text: str) -> dict[str, str]:
    lines = text.split("\n")
    sections: dict[str, str] = {}
    current_section = "header"
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip().lower()
        cleaned = stripped.strip("#").strip("*").strip(":").strip()

        if cleaned in _SECTION_HEADERS:
            if current_lines:
                sections[current_section] = "\n".join(current_lines)
            current_section = cleaned.replace(" ", "_")
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines)

    return sections
