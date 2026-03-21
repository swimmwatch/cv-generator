import typing
import uuid
from urllib.parse import urlparse

from core import domains
from core import dto
from core import repos
from utils.pagination import BasePagination


class JobService:
    def __init__(
        self,
        job_metadata_repo: repos.JobMetadataRepository,
        job_repo: repos.JobRepository,
    ) -> None:
        self._job_metadata_repo = job_metadata_repo
        self._job_repo = job_repo

    async def get_by_pk(self, pk: uuid.UUID) -> dto.JobOutDTO | None:
        return await self._job_repo.get_by_pk(pk)

    async def get_user_jobs(
        self,
        user_id: domains.UserID,
        pagination: BasePagination,
    ) -> tuple[list[dto.JobOutDTO], int]:
        return await self._job_repo.get_by_user_id(user_id=user_id, pagination=pagination)

    async def has_jobs(self, user_id: domains.UserID) -> bool:
        return await self._job_repo.has_jobs(user_id)

    async def delete(self, job: dto.JobOutDTO) -> None:
        await self._job_metadata_repo.delete_by_job_id(job.id)
        await self._job_repo.delete(pk=job.id)

    @staticmethod
    def normalize_url(url: str) -> str:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = parsed.path.rstrip("/")
        return f"{host}{path}"

    async def create_record(
        self,
        user_id: domains.UserID,
        title: str,
        url: str,
        metadata_: typing.Any = None,
    ) -> dto.JobOutDTO:
        normalized = self.normalize_url(url)
        return await self._job_repo.create_one(
            dto.JobCreateDTO(
                user_id=user_id,
                title=title,
                url=url,
                normalized_url=normalized,
                metadata_=metadata_,
            )
        )

    async def find_existing_job(self, url: str) -> dto.JobOutDTO | None:
        normalized = self.normalize_url(url)
        return await self._job_repo.find_by_normalized_url(normalized)

    async def copy_job_for_user(
        self,
        source_job: dto.JobOutDTO,
        user_id: domains.UserID,
        url: str,
    ) -> dto.JobOutDTO:
        new_job = await self.create_record(
            user_id=user_id,
            title=source_job.title,
            url=url,
            metadata_=source_job.metadata_,
        )
        full_text = await self.get_full_text(source_job.id)
        if full_text:
            await self.save_metadata(
                job_id=new_job.id,
                user_id=user_id,
                job_text=full_text,
            )
        return new_job

    async def save_metadata(
        self,
        job_id: domains.JobID,
        user_id: domains.UserID,
        job_text: str,
    ) -> list[domains.JobChunk]:
        chunks = domains.chunk_job(
            job_id=job_id,
            user_id=user_id,
            job_text=job_text,
        )
        await self._job_metadata_repo.delete_by_job_id(job_id)
        await self._job_metadata_repo.insert_chunks(chunks)
        return chunks

    async def get_full_text(self, job_id: domains.JobID) -> str | None:
        return await self._job_metadata_repo.get_full_text_by_job_id(job_id)

    async def search_by_text(
        self,
        query: str,
        job_id: domains.JobID,
        user_id: domains.UserID,
        limit: int = 10,
    ) -> list[str]:
        return await self._job_metadata_repo.search_by_text(
            query=query,
            job_id=job_id,
            user_id=user_id,
            limit=limit,
        )

    async def search_by_user(
        self,
        query: str,
        user_id: domains.UserID,
        limit: int = 10,
    ) -> list[str]:
        return await self._job_metadata_repo.search_by_user(
            query=query,
            user_id=user_id,
            limit=limit,
        )
