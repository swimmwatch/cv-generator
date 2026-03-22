import uuid

from core import domains
from core import dto
from core import repos
from utils.pagination import BasePagination
from utils.storages.impl.base import AsyncStorage


class ResumeService:
    def __init__(
        self,
        async_storage: AsyncStorage,
        resume_metadata_repo: repos.ResumeMetadataRepository,
        resume_repo: repos.ResumeRepository,
    ) -> None:
        self._async_storage = async_storage
        self._resume_metadata_repo = resume_metadata_repo
        self._resume_repo = resume_repo

    async def upload(
        self,
        user_id: domains.UserID,
        file_name: str,
        file_data: bytes,
        content_type: str,
    ) -> str:
        object_name = f"resume/{user_id}/{file_name}"
        await self._async_storage.put_bytes(
            object_name,
            file_data,
            content_type=content_type,
        )
        return object_name

    async def create_record(self, user_id: domains.UserID, object_name: str, file_name: str) -> dto.ResumeOutDTO:
        title = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        return await self._resume_repo.create_one(
            dto.ResumeCreateDTO(
                user_id=user_id,
                title=title,
                object_name=object_name,
                file_name=file_name,
            )
        )

    async def update_record_status(self, resume_id: uuid.UUID, status: domains.ResumeProcessingStatus) -> None:
        await self._resume_repo.update_status(pk=resume_id, status=status)

    async def update_record_title(self, resume_id: uuid.UUID, title: str) -> None:
        await self._resume_repo.update_title(pk=resume_id, title=title)

    async def get_by_pk(self, pk: uuid.UUID) -> dto.ResumeOutDTO | None:
        return await self._resume_repo.get_by_pk(pk)

    async def get_user_resumes(
        self,
        user_id: domains.UserID,
        pagination: BasePagination,
        status: domains.ResumeProcessingStatus | None = None,
    ) -> tuple[list[dto.ResumeOutDTO], int]:
        return await self._resume_repo.get_by_user_id(
            user_id=user_id,
            pagination=pagination,
            status=status,
        )

    async def has_done_resume(self, user_id: domains.UserID) -> bool:
        return await self._resume_repo.has_done_resume(user_id=user_id)

    async def delete(self, resume: dto.ResumeOutDTO) -> None:
        await self._resume_metadata_repo.delete_by_resume_id(resume.id)
        await self._async_storage.delete(resume.object_name)
        await self._resume_repo.delete(pk=resume.id)

    async def download(self, object_name: str) -> bytes:
        return await self._async_storage.get_bytes(object_name)

    async def save_metadata(
        self,
        resume_id: uuid.UUID,
        chunks: list[domains.ResumeChunk],
    ) -> None:
        await self._resume_metadata_repo.ensure_collection()
        await self._resume_metadata_repo.delete_by_resume_id(resume_id)
        await self._resume_metadata_repo.insert_chunks(chunks)

    async def search_by_text(
        self,
        query: str,
        resume_id: uuid.UUID,
        user_id: domains.UserID,
        limit: int = 10,
    ) -> list[str]:
        return await self._resume_metadata_repo.search_by_text(
            query=query,
            resume_id=resume_id,
            user_id=user_id,
            limit=limit,
        )

    async def search_by_user(
        self,
        query: str,
        user_id: domains.UserID,
        limit: int = 10,
    ) -> list[str]:
        return await self._resume_metadata_repo.search_by_user(
            query=query,
            user_id=user_id,
            limit=limit,
        )
