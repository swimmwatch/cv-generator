from enum import StrEnum
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from typing_extensions import TypedDict


class JobParserError(StrEnum):
    NOT_A_JOB_POSTING = "not_a_job_posting"
    MISSING_REQUIRED_FIELDS = "missing_required_fields"


class JobCard(BaseModel):
    is_job_posting: bool = Field(
        description="True if the text is a real job posting or vacancy. "
        "False if it is unrelated content (article, blog post, product page, gibberish, etc.)."
    )
    language_code: str = Field(default="en", description="ISO 639-1 language code of the job posting")
    job_title: str = Field(default="", description="Job title")
    company_name: Optional[str] = Field(default=None, description="Company name")
    employment_type: Optional[str] = Field(
        default=None, description="Employment type (full-time, part-time, contract, etc.)"
    )
    location: Optional[str] = Field(default=None, description="Location or Remote")
    seniority_level: Optional[str] = Field(
        default=None, description="Seniority level (Junior, Middle, Senior, Lead, etc.)"
    )
    required_skills: list[str] = Field(default_factory=list, description="Required/mandatory skills and technologies")
    nice_to_have_skills: list[str] = Field(default_factory=list, description="Nice-to-have/optional skills")
    responsibilities: list[str] = Field(default_factory=list, description="Key job responsibilities")
    requirements: list[str] = Field(
        default_factory=list, description="Formal requirements (experience, education, etc.)"
    )
    conditions: list[str] = Field(
        default_factory=list, description="Work conditions (remote, flexible hours, salary, etc.)"
    )
    summary: str = Field(default="", description="Brief summary of the job posting in 1-3 sentences")
    text: str = Field(
        default="",
        description="Full job posting text, cleaned of navigation, ads, headers, footers, "
        "and other non-essential content. Keep only the actual job description.",
    )


class JobParserResult(BaseModel):
    success: bool
    result: Optional[JobCard] = None
    error: Optional[str] = None


class AgentState(TypedDict):
    job_reference: str
    page_content: Optional[str]
    parsed_result: Optional[JobCard]
    error: Optional[str]
    retries: int
