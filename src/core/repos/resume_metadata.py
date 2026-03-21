import typing
import uuid

from core import dal
from core import domains


class ResumeMetadataRepository(typing.Protocol):
    async def ensure_collection(self) -> None:
        pass

    async def delete_by_resume_id(self, resume_id: uuid.UUID) -> None:
        pass

    async def delete_by_user_id(self, user_id: uuid.UUID) -> None:
        pass

    async def insert_chunks(self, chunks: list[domains.ResumeChunk]) -> None:
        pass

    async def search_by_text(
        self,
        query: str,
        resume_id: uuid.UUID,
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


class WeaviateResumeMetadataRepository:
    def __init__(self, resume_metadata_dal: dal.ResumeMetadataDAL) -> None:
        self._dal = resume_metadata_dal

    async def ensure_collection(self) -> None:
        await self._dal.ensure_collection()

    async def delete_by_resume_id(self, resume_id: uuid.UUID) -> None:
        await self._dal.delete_by_resume_id(str(resume_id))

    async def delete_by_user_id(self, user_id: uuid.UUID) -> None:
        await self._dal.delete_by_user_id(str(user_id))

    async def insert_chunks(self, chunks: list[domains.ResumeChunk]) -> None:
        await self._dal.insert_chunks(chunks)

    async def search_by_text(
        self,
        query: str,
        resume_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[str]:
        return await self._dal.search_by_text(
            query=query,
            resume_id=str(resume_id),
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
