import uuid

from core import domains
from core import dto
from core import repos
from utils.pagination import BasePagination
from utils.storages.impl.base import AsyncStorage


class GeneratedCVService:
    def __init__(
        self,
        async_storage: AsyncStorage,
        generated_cv_repo: repos.GeneratedCVRepository,
    ) -> None:
        self._async_storage = async_storage
        self._generated_cv_repo = generated_cv_repo

    async def save(
        self,
        user_id: domains.UserID,
        resume_id: uuid.UUID,
        job_id: uuid.UUID,
        file_name: str,
        file_data: bytes,
    ) -> dto.GeneratedCVOutDTO:
        object_name = f"generated_cv/{user_id}/{file_name}"
        await self._async_storage.put_bytes(
            object_name,
            file_data,
            content_type="application/pdf",
        )
        return await self._generated_cv_repo.create_one(
            dto.GeneratedCVCreateDTO(
                user_id=user_id,
                resume_id=resume_id,
                job_id=job_id,
                object_name=object_name,
                file_name=file_name,
            )
        )

    async def get_by_pk(self, pk: uuid.UUID) -> dto.GeneratedCVOutDTO | None:
        return await self._generated_cv_repo.get_by_pk(pk)

    async def get_user_generated_cvs(
        self,
        user_id: domains.UserID,
        pagination: BasePagination,
    ) -> tuple[list[dto.GeneratedCVOutDTO], int]:
        return await self._generated_cv_repo.get_by_user_id(
            user_id=user_id,
            pagination=pagination,
        )

    async def download(self, object_name: str) -> bytes:
        return await self._async_storage.get_bytes(object_name)
