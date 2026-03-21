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
async def search_resumes(
    ctx: RunContext[ChatDeps],
    query: str,
    limit: int = 5,
) -> list[str]:
    """Search the user's resume by semantic similarity.

    Use this tool to find relevant parts of the user's resume
    that match a given query. Returns a list of matching text chunks.
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

    Use this tool to find relevant parts of a job posting
    that match a given query. Returns a list of matching text chunks.
    """
    return await ctx.deps.job_metadata_repo.search_by_text(
        query=query[:_MAX_SEARCH_QUERY_LENGTH],
        job_id=uuid.UUID(ctx.deps.job_id),
        user_id=uuid.UUID(ctx.deps.user_id),
        limit=min(limit, _MAX_SEARCH_LIMIT),
    )
