import typing
from dataclasses import dataclass
from dataclasses import field

from .resume import ResumeID
from .user import UserID


@dataclass(slots=True)
class ResumeContacts:
    email: str = ""
    location: str = ""
    links: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResumeHeader:
    user_id: str = ""
    first_name: str = ""
    last_name: str = ""
    title: str = ""
    contacts: ResumeContacts = field(default_factory=ResumeContacts)


@dataclass(slots=True)
class ResumeExperience:
    company: str = ""
    role: str = ""
    period: str = ""
    bullets: list[str] = field(default_factory=list)
    tech: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResumeProject:
    name: str = ""
    description: str = ""
    highlights: list[str] = field(default_factory=list)
    tech: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResumeSkills:
    primary: list[str] = field(default_factory=list)
    secondary: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResumeAdditional:
    languages: list[str] = field(default_factory=list)
    certificates: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResumeMetadata:
    header: ResumeHeader = field(default_factory=ResumeHeader)
    summary: list[str] = field(default_factory=list)
    skills: ResumeSkills = field(default_factory=ResumeSkills)
    experience: list[ResumeExperience] = field(default_factory=list)
    projects: list[ResumeProject] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    additional: ResumeAdditional = field(default_factory=ResumeAdditional)


@dataclass(slots=True)
class ResumeChunk:
    resume_id: str
    user_id: str
    section: str
    content: str
    metadata: dict[str, typing.Any]


def build_resume_metadata(
    user_id: UserID,
    first_name: str,
    last_name: str,
    resume_text: str,
) -> ResumeMetadata:
    return ResumeMetadata(
        header=ResumeHeader(
            user_id=str(user_id),
            first_name=first_name,
            last_name=last_name,
        ),
    )


def chunk_resume(
    resume_id: ResumeID,
    user_id: UserID,
    first_name: str,
    last_name: str,
    resume_text: str,
) -> list[ResumeChunk]:
    str_resume_id = str(resume_id)
    str_user_id = str(user_id)
    base_metadata = {
        "resume_id": str_resume_id,
        "user_id": str_user_id,
        "first_name": first_name,
        "last_name": last_name,
    }
    chunks: list[ResumeChunk] = []

    chunks.append(
        ResumeChunk(
            resume_id=str_resume_id,
            user_id=str_user_id,
            section="full_resume",
            content=resume_text,
            metadata=base_metadata,
        )
    )

    sections = _split_into_sections(resume_text)
    for section_name, section_text in sections.items():
        if section_text.strip():
            chunks.append(
                ResumeChunk(
                    resume_id=str_resume_id,
                    user_id=str_user_id,
                    section=section_name,
                    content=section_text.strip(),
                    metadata={**base_metadata, "section": section_name},
                )
            )

    return chunks


_SECTION_HEADERS = [
    "summary",
    "objective",
    "experience",
    "work experience",
    "employment",
    "projects",
    "education",
    "skills",
    "technical skills",
    "certificates",
    "certifications",
    "languages",
    "additional",
    "interests",
    "awards",
    "publications",
    "references",
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


def extract_title_from_resume_text(text: str) -> str | None:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    found_name = False
    for line in lines[:10]:
        if "@" in line or "http" in line.lower():
            continue
        words = line.split()
        if not found_name:
            found_name = True
            continue
        if 1 < len(words) <= 8:
            return line[:256]
    return None
