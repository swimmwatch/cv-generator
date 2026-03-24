import typing
import uuid

from core import dal
from core import domains


class JobMetadataRepository(typing.Protocol):
    async def ensure_collection(self) -> None:
        pass

    async def delete_by_job_id(self, job_id: uuid.UUID) -> None:
        pass

    async def insert_chunks(self, chunks: list[domains.JobChunk]) -> None:
        pass

    async def get_full_text_by_job_id(self, job_id: uuid.UUID) -> str | None:
        pass

    async def get_chunks_by_job_id(self, job_id: uuid.UUID) -> list[domains.JobChunk]:
        pass

    async def search_by_text(
        self,
        query: str,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[str]:
        pass

    async def search_by_user(
        self,
        query: str,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[str]:
        pass


class WeaviateJobMetadataRepository:
    def __init__(self, job_metadata_dal: dal.JobMetadataDAL) -> None:
        self._dal = job_metadata_dal

    async def ensure_collection(self) -> None:
        await self._dal.ensure_collection()

    async def delete_by_job_id(self, job_id: uuid.UUID) -> None:
        await self._dal.delete_by_job_id(str(job_id))

    async def insert_chunks(self, chunks: list[domains.JobChunk]) -> None:
        await self._dal.insert_chunks(chunks)

    async def get_full_text_by_job_id(self, job_id: uuid.UUID) -> str | None:
        return await self._dal.get_full_text_by_job_id(str(job_id))

    async def get_chunks_by_job_id(self, job_id: uuid.UUID) -> list[domains.JobChunk]:
        return await self._dal.get_chunks_by_job_id(str(job_id))

    async def search_by_text(
        self,
        query: str,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[str]:
        return await self._dal.search_by_text(
            query=query,
            job_id=str(job_id),
            user_id=str(user_id),
            limit=limit,
        )

    async def search_by_user(
        self,
        query: str,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[str]:
        return await self._dal.search_by_user(
            query=query,
            user_id=str(user_id),
            limit=limit,
        )
