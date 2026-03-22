import uuid
from dataclasses import dataclass

from pydantic_ai import FunctionToolset
from pydantic_ai import RunContext

from core import repos

_MAX_SEARCH_QUERY_LENGTH = 500
_MAX_SEARCH_LIMIT = 10


@dataclass
class ChatDeps:
    resume_metadata_repo: repos.ResumeMetadataRepository
    job_metadata_repo: repos.JobMetadataRepository
    user_id: str
    resume_id: str
    job_id: str


chat_toolset: FunctionToolset[ChatDeps] = FunctionToolset()


@chat_toolset.tool
async def get_resume_content(ctx: RunContext[ChatDeps]) -> list[str]:
    """Retrieve ALL content from the user's selected resume.

    Use this tool when you need comprehensive resume information,
    e.g. for writing cover letters, summarizing, or comparing with a job.
    Returns all text chunks of the resume.
    """
    return await ctx.deps.resume_metadata_repo.get_chunks_by_resume_id(
        resume_id=uuid.UUID(ctx.deps.resume_id),
    )


@chat_toolset.tool
async def get_job_content(ctx: RunContext[ChatDeps]) -> list[str]:
    """Retrieve ALL content from the selected job posting.

    Use this tool when you need comprehensive job information,
    e.g. for writing cover letters, comparing with a resume, or summarizing a job.
    Returns all text chunks of the job posting.
    """
    chunks = await ctx.deps.job_metadata_repo.get_chunks_by_job_id(
        job_id=uuid.UUID(ctx.deps.job_id),
    )
    return [chunk.content for chunk in chunks]


@chat_toolset.tool
async def search_resumes(
    ctx: RunContext[ChatDeps],
    query: str,
    limit: int = 5,
) -> list[str]:
    """Search the user's resume by semantic similarity.

    Use this tool to find specific parts of the resume matching a query.
    The query must describe the CONTENT you are looking for, not meta-terms.
    Good queries: "Python experience", "education", "team leadership".
    Bad queries: "resume", "резюме", "all information".
    For comprehensive retrieval, use get_resume_content instead.
    """
    return await ctx.deps.resume_metadata_repo.search_by_text(
        query=query[:_MAX_SEARCH_QUERY_LENGTH],
        resume_id=uuid.UUID(ctx.deps.resume_id),
        user_id=uuid.UUID(ctx.deps.user_id),
        limit=min(limit, _MAX_SEARCH_LIMIT),
    )


@chat_toolset.tool
async def search_jobs(
    ctx: RunContext[ChatDeps],
    query: str,
    limit: int = 5,
) -> list[str]:
    """Search job postings by semantic similarity.

    Use this tool to find specific parts of a job posting matching a query.
    The query must describe the CONTENT you are looking for, not meta-terms.
    Good queries: "required skills", "salary", "responsibilities".
    Bad queries: "job", "вакансия", "all information".
    For comprehensive retrieval, use get_job_content instead.
    """
    return await ctx.deps.job_metadata_repo.search_by_text(
        query=query[:_MAX_SEARCH_QUERY_LENGTH],
        job_id=uuid.UUID(ctx.deps.job_id),
        user_id=uuid.UUID(ctx.deps.user_id),
        limit=min(limit, _MAX_SEARCH_LIMIT),
    )
