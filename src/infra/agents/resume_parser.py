import typing
from dataclasses import dataclass

import httpx
import logfire
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.openai import OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from core import domains
from core.errors.resumes import InvalidResumeError
from infra.agents.schemas.resume import ResumePayload


@dataclass(slots=True)
class ResumeParseResult:
    title: str
    chunks: list[domains.ResumeChunk]


_INSTRUCTIONS = """\
You are a resume parser. Your task is to extract structured information \
from a raw resume text and return it in the specified JSON format.

Rules:
- First, determine if the provided text is a real resume or CV. \
Set "is_resume" to true only if the text contains professional information \
such as work experience, education, skills, or contact details of a person. \
If the text is unrelated content (a recipe, article, random text, gibberish, etc.), \
set "is_resume" to false and leave all other fields at their defaults.
- Preserve the original language of the resume. Do not translate any content.
- Extract ALL information present in the resume. Do not omit any section.
- If a field is not present in the resume, leave it empty or use the default value.
- For the "about" field: extract the professional summary or objective. \
You may use <strong> tags to emphasize key technologies or skills.
- For experience entries: each bullet in "description" should be a concise, \
impactful statement about achievements or responsibilities.
- For "stack" in experience: extract the technologies used in that specific role.
- For "skills": list all skills mentioned, prioritized by prominence in the resume. \
Include language proficiency if present.
- For contacts: extract email, phone, telegram handle, and location if available.
- "title" should reflect the candidate's current or target professional title.\
"""


ReasoningEffort = typing.Literal["minimal", "low", "medium", "high"]


class ResumeParser:
    def __init__(
        self,
        model_name: str,
        model_token: str,
        temperature: float = 0.0,
        max_tokens: int = 16384,
        timeout: float = 60.0,
        top_p: float = 1.0,
        reasoning_effort: ReasoningEffort = "low",
    ) -> None:
        model = OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(api_key=model_token),
        )
        self._agent = Agent(
            model,
            output_type=ResumePayload,
            instructions=_INSTRUCTIONS,
            model_settings=OpenAIChatModelSettings(
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                top_p=top_p,
                openai_reasoning_effort=reasoning_effort,
            ),
        )

    async def parse(
        self,
        resume_text: str,
        resume_id: domains.ResumeID,
        user_id: domains.UserID,
    ) -> ResumeParseResult:
        with logfire.span("resume_parser.parse", text_length=len(resume_text)):
            try:
                async with self._agent as agent:
                    result = await agent.run(resume_text)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                logfire.error("resume_parser.parse connection failed", error=str(exc))
                raise

            payload = result.output

            if not payload.is_resume:
                raise InvalidResumeError()

            chunks = self._chunk(
                resume_id=resume_id,
                user_id=user_id,
                resume_text=resume_text,
                payload=payload,
            )
            return ResumeParseResult(title=payload.title, chunks=chunks)

    def _chunk(
        self,
        resume_id: domains.ResumeID,
        user_id: domains.UserID,
        resume_text: str,
        payload: ResumePayload,
    ) -> list[domains.ResumeChunk]:
        str_resume_id = str(resume_id)
        str_user_id = str(user_id)
        name_parts = payload.full_name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        base_metadata = {
            "resume_id": str_resume_id,
            "user_id": str_user_id,
            "first_name": first_name,
            "last_name": last_name,
        }

        chunks: list[domains.ResumeChunk] = []

        chunks.append(
            domains.ResumeChunk(
                resume_id=str_resume_id,
                user_id=str_user_id,
                section="full_resume",
                content=resume_text,
                metadata=base_metadata,
            )
        )

        if payload.about:
            chunks.append(
                domains.ResumeChunk(
                    resume_id=str_resume_id,
                    user_id=str_user_id,
                    section="about",
                    content=payload.about,
                    metadata={**base_metadata, "section": "about"},
                )
            )

        if payload.skills:
            chunks.append(
                domains.ResumeChunk(
                    resume_id=str_resume_id,
                    user_id=str_user_id,
                    section="skills",
                    content=", ".join(payload.skills),
                    metadata={**base_metadata, "section": "skills"},
                )
            )

        for exp in payload.experience:
            parts = [f"{exp.position} at {exp.company} ({exp.period})"]
            parts.extend(exp.description)
            if exp.stack:
                parts.append(f"Technologies: {', '.join(exp.stack)}")
            chunks.append(
                domains.ResumeChunk(
                    resume_id=str_resume_id,
                    user_id=str_user_id,
                    section="experience",
                    content="\n".join(parts),
                    metadata={
                        **base_metadata,
                        "section": "experience",
                        "company": exp.company,
                        "position": exp.position,
                    },
                )
            )

        for edu in payload.education:
            chunks.append(
                domains.ResumeChunk(
                    resume_id=str_resume_id,
                    user_id=str_user_id,
                    section="education",
                    content=f"{edu.degree} — {edu.institution} ({edu.period})",
                    metadata={**base_metadata, "section": "education"},
                )
            )

        return chunks
