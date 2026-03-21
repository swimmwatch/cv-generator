from aiogram.filters import BaseFilter
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import dto
from core import repos
from core import services


class HasDoneResumeFilter(BaseFilter):
    @inject
    async def __call__(
        self,
        message: Message,
        user: dto.UserOutDTO,
        resume_service: services.ResumeService = Provide["resume_service"],
    ) -> bool:
        return await resume_service.has_done_resume(user.id)


class NoActiveJobParsingFilter(BaseFilter):
    @inject
    async def __call__(
        self,
        message: Message,
        user: dto.UserOutDTO,
        job_state_repo: repos.JobStateRepository = Provide["redis_job_state_repo"],
    ) -> bool:
        return not await job_state_repo.is_active(user.id)


class HasJobFilter(BaseFilter):
    @inject
    async def __call__(
        self,
        message: Message,
        user: dto.UserOutDTO,
        job_service: services.JobService = Provide["job_service"],
    ) -> bool:
        return await job_service.has_jobs(user.id)
