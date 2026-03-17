import typing
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from core import dal
from core import dto
from utils.pagination import BasePagination


class JobRepository(typing.Protocol):
    async def create_one(self, data: dto.JobCreateDTO) -> dto.JobOutDTO:
        pass

    async def get_by_pk(self, pk: uuid.UUID) -> dto.JobOutDTO | None:
        pass

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        pagination: BasePagination,
    ) -> tuple[list[dto.JobOutDTO], int]:
        pass


class SqlAlchemyJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._job_dal = dal.JobAsyncDAL(session)

    async def create_one(self, data: dto.JobCreateDTO) -> dto.JobOutDTO:
        job = await self._job_dal.create_one(
            user_id=data.user_id,
            title=data.title,
            url=data.url,
            metadata_=data.metadata_,
        )
        return dto.JobOutDTO.from_model(job)

    async def get_by_pk(self, pk: uuid.UUID) -> dto.JobOutDTO | None:
        job = await self._job_dal.filter(id=pk).first()
        if not job:
            return None
        return dto.JobOutDTO.from_model(job)

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        pagination: BasePagination,
    ) -> tuple[list[dto.JobOutDTO], int]:
        total = await self._job_dal.filter(user_id=user_id).count()
        limit, offset = pagination.get_limit_offset()
        query = self._job_dal.filter(user_id=user_id).order_by(created_at=True)
        items: list[typing.Any] = await query.limit(limit).offset(offset).scalars()
        return [dto.JobOutDTO.from_model(j) for j in items], total
