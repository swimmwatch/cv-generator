from unittest.mock import AsyncMock

import pytest

from core import repos
from core import services
from utils.storages.impl.base import AsyncStorage


@pytest.fixture
def user_service(sql_user_repo: repos.SqlAlchemyUserRepository) -> services.UserService:
    return services.UserService(sql_user_repo)


@pytest.fixture
def job_metadata_repo() -> AsyncMock:
    return AsyncMock(spec=repos.JobMetadataRepository)


@pytest.fixture
def job_service(
    job_metadata_repo: AsyncMock,
    sql_job_repo: repos.SqlAlchemyJobRepository,
) -> services.JobService:
    return services.JobService(
        job_metadata_repo=job_metadata_repo,
        job_repo=sql_job_repo,
    )


@pytest.fixture
def async_storage() -> AsyncMock:
    return AsyncMock(spec=AsyncStorage)


@pytest.fixture
def resume_metadata_repo() -> AsyncMock:
    return AsyncMock(spec=repos.ResumeMetadataRepository)


@pytest.fixture
def resume_service(
    async_storage: AsyncMock,
    resume_metadata_repo: AsyncMock,
    sql_resume_repo: repos.SqlAlchemyResumeRepository,
) -> services.ResumeService:
    return services.ResumeService(
        async_storage=async_storage,
        resume_metadata_repo=resume_metadata_repo,
        resume_repo=sql_resume_repo,
    )
