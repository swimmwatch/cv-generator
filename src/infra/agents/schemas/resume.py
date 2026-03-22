from pydantic import BaseModel
from pydantic import Field


class ResumeContacts(BaseModel):
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    telegram: str = Field(default="", description="Telegram handle")
    location: str = Field(default="", description="City, Country")


class ResumeExperience(BaseModel):
    position: str = Field(description="Job title/position")
    company: str = Field(description="Company name")
    period: str = Field(description="Employment period")
    description: list[str] = Field(
        default_factory=list,
        description="Bullet points describing key achievements and responsibilities. "
        "Each bullet should be a concise, impactful statement.",
    )
    stack: list[str] = Field(default_factory=list, description="Technologies used in this role")


class ResumeEducation(BaseModel):
    period: str = Field(description="Education period")
    degree: str = Field(description="Degree obtained")
    institution: str = Field(description="Educational institution name")


class ResumePayload(BaseModel):
    is_resume: bool = Field(
        description="True if the text is a real resume/CV. "
        "False if it is unrelated content (recipe, article, gibberish, etc.)."
    )
    full_name: str = Field(default="", description="Full name of the candidate")
    title: str = Field(default="", description="Professional title, tailored to the target vacancy")
    contacts: ResumeContacts = Field(default_factory=ResumeContacts, description="Contact information")
    about: str = Field(
        description="Professional summary tailored to the vacancy. "
        "May use <strong> tags for emphasis on key technologies. 1-3 sentences."
    )
    skills: list[str] = Field(
        description="List of skills, prioritized by relevance to the target vacancy. "
        "Include language proficiency if present in the source resume."
    )
    experience: list[ResumeExperience] = Field(
        description="Work experience entries, ordered by relevance. "
        "Descriptions should be tailored to highlight achievements relevant to the vacancy."
    )
    education: list[ResumeEducation] = Field(default_factory=list, description="Education entries")
