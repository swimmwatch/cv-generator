import typing
import uuid

from core import dal
from core import domains
from core import dto
from core import repos
from utils.pagination import BasePagination


class JobService:
    def __init__(
        self,
        job_metadata_dal: dal.JobMetadataDAL,
        job_repo: repos.JobRepository,
    ) -> None:
        self._job_metadata_dal = job_metadata_dal
        self._job_repo = job_repo

    async def get_user_jobs(
        self,
        user_id: domains.UserID,
        pagination: BasePagination,
    ) -> tuple[list[dto.JobOutDTO], int]:
        return await self._job_repo.get_by_user_id(user_id=user_id, pagination=pagination)

    async def create_record(
        self,
        user_id: domains.UserID,
        resume_id: uuid.UUID,
        title: str,
        url: str,
        metadata_: typing.Any = None,
    ) -> dto.JobOutDTO:
        return await self._job_repo.create_one(
            dto.JobCreateDTO(
                user_id=user_id,
                resume_id=resume_id,
                title=title,
                url=url,
                metadata_=metadata_,
            )
        )

    async def save_metadata(
        self,
        job_id: domains.JobID,
        user_id: domains.UserID,
        resume_id: uuid.UUID,
        job_text: str,
    ) -> list[domains.JobChunk]:
        chunks = domains.chunk_job(
            job_id=job_id,
            user_id=user_id,
            resume_id=str(resume_id),
            job_text=job_text,
        )
        await self._job_metadata_dal.delete_by_job_id(str(job_id))
        await self._job_metadata_dal.insert_chunks(chunks)
        return chunks
