from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from typing_extensions import TypedDict

from infra.agents.schemas.resume import ResumePayload


class VacancySignals(BaseModel):
    title_signals: list[str] = Field(description="Role title variants, seniority indicators, domain keywords")
    about_signals: list[str] = Field(description="Key themes for professional summary, core competencies needed")
    skills_signals: list[str] = Field(description="Required and preferred skills, technologies, tools, methodologies")
    experience_signals: list[str] = Field(description="Experience types valued, years, domains, achievement patterns")
    education_signals: list[str] = Field(description="Required degrees, certifications, knowledge areas")


class VacancyAnalysis(BaseModel):
    signals: VacancySignals = Field(description="Extracted signals per template section")
    search_queries: list[str] = Field(
        description="5-10 targeted queries for resume chunk retrieval from vector database"
    )


class EvidenceItem(BaseModel):
    requirement: str = Field(description="Vacancy requirement or signal")
    evidence: str = Field(description="Supporting resume evidence text")
    template_field: str = Field(description="Target template field: title, about, skills, experience, or education")
    evidence_type: str = Field(description="Classification: direct, adjacent, or unsupported")


class EvidenceMap(BaseModel):
    items: list[EvidenceItem] = Field(description="Mapped evidence items with classifications")


class CvGeneratorState(TypedDict):
    user_id: str
    job_text: str
    job_title: str
    job_id: str
    resume_id: str
    template_json: str
    vacancy_analysis: Optional[VacancyAnalysis]
    evidence_map: Optional[EvidenceMap]
    tailored_result: Optional[ResumePayload]
    error: Optional[str]
    retries: int


class CvGeneratorResult(BaseModel):
    success: bool
    result: Optional[ResumePayload] = None
