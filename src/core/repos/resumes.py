import typing
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core import dal
from core import domains
from core import dto
from utils.pagination import BasePagination


class ResumeRepository(typing.Protocol):
    async def create_one(self, data: dto.ResumeCreateDTO) -> dto.ResumeOutDTO:
        pass

    async def get_by_pk(self, pk: uuid.UUID) -> dto.ResumeOutDTO | None:
        pass

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        pagination: BasePagination,
        status: domains.ResumeProcessingStatus | None = None,
    ) -> tuple[list[dto.ResumeOutDTO], int]:
        pass

    async def has_done_resume(self, user_id: uuid.UUID) -> bool:
        pass

    async def update_status(self, pk: uuid.UUID, status: domains.ResumeProcessingStatus) -> None:
        pass

    async def update_title(self, pk: uuid.UUID, title: str) -> None:
        pass

    async def delete(self, pk: uuid.UUID) -> None:
        pass


class SqlAlchemyResumeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._resume_dal = dal.ResumeAsyncDAL(session)

    async def create_one(self, data: dto.ResumeCreateDTO) -> dto.ResumeOutDTO:
        resume = await self._resume_dal.create_one(
            user_id=data.user_id,
            title=data.title,
            object_name=data.object_name,
            file_name=data.file_name,
            status=data.status,
        )
        return dto.ResumeOutDTO.from_model(resume)

    async def get_by_pk(self, pk: uuid.UUID) -> dto.ResumeOutDTO | None:
        resume = await self._resume_dal.filter(id=pk).first()
        if not resume:
            return None
        return dto.ResumeOutDTO.from_model(resume)

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        pagination: BasePagination,
        status: domains.ResumeProcessingStatus | None = None,
    ) -> tuple[list[dto.ResumeOutDTO], int]:
        filters: dict[str, typing.Any] = {"user_id": user_id}
        if status is not None:
            filters["status"] = status
        total = await self._resume_dal.filter(**filters).count()
        limit, offset = pagination.get_limit_offset()
        dal_query = self._resume_dal.filter(**filters).order_by(created_at=True)
        items: list[typing.Any] = await dal_query.limit(limit).offset(offset).scalars()
        return [dto.ResumeOutDTO.from_model(r) for r in items], total

    async def has_done_resume(self, user_id: uuid.UUID) -> bool:
        count = await self._resume_dal.filter(
            user_id=user_id,
            status=domains.ResumeProcessingStatus.DONE,
        ).count()
        return count > 0

    async def update_status(self, pk: uuid.UUID, status: domains.ResumeProcessingStatus) -> None:
        await self._resume_dal.filter(id=pk).update(status=status)

    async def update_title(self, pk: uuid.UUID, title: str) -> None:
        await self._resume_dal.filter(id=pk).update(title=title)

    async def delete(self, pk: uuid.UUID) -> None:
        await self._resume_dal.filter(id=pk).delete()
