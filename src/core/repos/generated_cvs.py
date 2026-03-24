import typing
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core import dal
from core import dto
from utils.pagination import BasePagination


class GeneratedCVRepository(typing.Protocol):
    async def create_one(self, data: dto.GeneratedCVCreateDTO) -> dto.GeneratedCVOutDTO:
        pass

    async def get_by_pk(self, pk: uuid.UUID) -> dto.GeneratedCVOutDTO | None:
        pass

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        pagination: BasePagination,
    ) -> tuple[list[dto.GeneratedCVOutDTO], int]:
        pass


class SqlAlchemyGeneratedCVRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._dal = dal.GeneratedCVAsyncDAL(session)

    async def create_one(self, data: dto.GeneratedCVCreateDTO) -> dto.GeneratedCVOutDTO:
        instance = await self._dal.create_one(
            user_id=data.user_id,
            resume_id=data.resume_id,
            job_id=data.job_id,
            object_name=data.object_name,
            file_name=data.file_name,
        )
        return dto.GeneratedCVOutDTO.from_model(instance)

    async def get_by_pk(self, pk: uuid.UUID) -> dto.GeneratedCVOutDTO | None:
        instance = await self._dal.filter(id=pk).first()
        if not instance:
            return None
        return dto.GeneratedCVOutDTO.from_model(instance)

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        pagination: BasePagination,
    ) -> tuple[list[dto.GeneratedCVOutDTO], int]:
        total = await self._dal.filter(user_id=user_id).count()
        limit, offset = pagination.get_limit_offset()
        query = self._dal.filter(user_id=user_id).order_by(created_at=True)
        items: list[typing.Any] = await query.limit(limit).offset(offset).scalars()
        return [dto.GeneratedCVOutDTO.from_model(i) for i in items], total
