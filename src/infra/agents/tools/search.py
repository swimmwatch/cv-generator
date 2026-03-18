from dataclasses import dataclass

import logfire
from pydantic_ai import FunctionToolset
from pydantic_ai import RunContext

from core import dal


@dataclass
class SearchDeps:
    resume_metadata_dal: dal.ResumeMetadataDAL
    job_metadata_dal: dal.JobMetadataDAL
    resume_id: str
    job_id: str


search_toolset: FunctionToolset[SearchDeps] = FunctionToolset()


@search_toolset.tool
async def search_resume_chunks(
    ctx: RunContext[SearchDeps],
    query: str,
    limit: int = 5,
) -> list[str]:
    """Search resume chunks by semantic similarity.

    Use this tool to find relevant parts of the candidate's resume
    that match a given query. Returns a list of matching text chunks.
    """
    with logfire.span(
        "tool.search_resume_chunks",
        resume_id=ctx.deps.resume_id,
        query=query,
        limit=limit,
    ):
        results = await ctx.deps.resume_metadata_dal.search_by_text(
            query=query,
            resume_id=ctx.deps.resume_id,
            limit=limit,
        )
        logfire.info("search_resume_chunks results", count=len(results))
        return results


@search_toolset.tool
async def search_vacancy_chunks(
    ctx: RunContext[SearchDeps],
    query: str,
    limit: int = 5,
) -> list[str]:
    """Search vacancy chunks by semantic similarity.

    Use this tool to find relevant parts of the job vacancy
    that match a given query. Returns a list of matching text chunks.
    """
    with logfire.span(
        "tool.search_vacancy_chunks",
        job_id=ctx.deps.job_id,
        query=query,
        limit=limit,
    ):
        results = await ctx.deps.job_metadata_dal.search_by_text(
            query=query,
            job_id=ctx.deps.job_id,
            limit=limit,
        )
        logfire.info("search_vacancy_chunks results", count=len(results))
        return results
