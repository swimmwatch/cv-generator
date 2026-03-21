import uuid

from core import dto
from core import models
from core import repos
from tests.factories import JobFactory
from tests.factories import UserFactory
from utils.pagination import PageSizePagination


class TestSqlAlchemyJobRepositoryCreateOne:
    async def test_creates_job(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.JobCreateDTO(
            user_id=user.id,
            title="Software Engineer",
            url="https://example.com/job/1",
            normalized_url="example.com/job/1",
        )
        result = await sql_job_repo.create_one(data)

        assert result.user_id == user.id
        assert result.title == "Software Engineer"
        assert result.url == "https://example.com/job/1"
        assert result.id is not None

    async def test_creates_job_with_metadata(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        metadata = {"skills": ["python", "sql"], "level": "senior"}
        data = dto.JobCreateDTO(
            user_id=user.id,
            title="Backend Dev",
            url="https://example.com/job/2",
            normalized_url="example.com/job/2",
            metadata_=metadata,
        )
        result = await sql_job_repo.create_one(data)

        assert result.metadata_ == metadata

    async def test_creates_job_without_metadata(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.JobCreateDTO(
            user_id=user.id,
            title="DevOps",
            url="https://example.com/job/3",
            normalized_url="example.com/job/3",
        )
        result = await sql_job_repo.create_one(data)

        assert result.metadata_ is None


class TestSqlAlchemyJobRepositoryGetByPk:
    async def test_returns_job(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        job: models.Job = await job_factory.create_async(user_id=user.id)

        result = await sql_job_repo.get_by_pk(job.id)

        assert result is not None
        assert result.id == job.id
        assert result.title == job.title

    async def test_returns_none_for_nonexistent_pk(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
    ) -> None:
        result = await sql_job_repo.get_by_pk(uuid.uuid4())

        assert result is None


class TestSqlAlchemyJobRepositoryGetByUserId:
    async def test_returns_user_jobs(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user.id)
        await job_factory.create_async(user_id=user.id)

        items, total = await sql_job_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 2
        assert len(items) == 2

    async def test_returns_empty_for_user_without_jobs(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
    ) -> None:
        items, total = await sql_job_repo.get_by_user_id(
            user_id=uuid.uuid4(),
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 0
        assert items == []

    async def test_does_not_return_other_users_jobs(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user1.id)
        await job_factory.create_async(user_id=user2.id)

        items, total = await sql_job_repo.get_by_user_id(
            user_id=user1.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].user_id == user1.id

    async def test_paginates_results(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        for _ in range(5):
            await job_factory.create_async(user_id=user.id)

        items_p1, total = await sql_job_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=2, page=1),
        )

        assert total == 5
        assert len(items_p1) == 2

        items_p3, _ = await sql_job_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=2, page=3),
        )

        assert len(items_p3) == 1

    async def test_page_beyond_total_returns_empty(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user.id)

        items, total = await sql_job_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=99),
        )

        assert total == 1
        assert items == []


class TestSqlAlchemyJobRepositoryHasJobs:
    async def test_returns_true_when_jobs_exist(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user.id)

        assert await sql_job_repo.has_jobs(user.id) is True

    async def test_returns_true_when_multiple_jobs_exist(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user.id)
        await job_factory.create_async(user_id=user.id)

        assert await sql_job_repo.has_jobs(user.id) is True

    async def test_returns_false_when_no_jobs(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
    ) -> None:
        assert await sql_job_repo.has_jobs(uuid.uuid4()) is False

    async def test_returns_false_when_only_other_user_has_jobs(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user2.id)

        assert await sql_job_repo.has_jobs(user1.id) is False


class TestSqlAlchemyJobRepositoryDelete:
    async def test_deletes_job(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        job: models.Job = await job_factory.create_async(user_id=user.id)

        await sql_job_repo.delete(pk=job.id)

        assert await sql_job_repo.get_by_pk(job.id) is None

    async def test_does_not_affect_other_jobs(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        job1: models.Job = await job_factory.create_async(user_id=user.id)
        job2: models.Job = await job_factory.create_async(user_id=user.id)

        await sql_job_repo.delete(pk=job1.id)

        assert await sql_job_repo.get_by_pk(job1.id) is None
        assert await sql_job_repo.get_by_pk(job2.id) is not None


class TestSqlAlchemyJobRepositoryFindByNormalizedUrl:
    async def test_returns_job_when_found(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(
            user_id=user.id,
            normalized_url="example.com/jobs/123",
        )

        result = await sql_job_repo.find_by_normalized_url("example.com/jobs/123")

        assert result is not None
        assert result.normalized_url == "example.com/jobs/123"

    async def test_returns_none_when_not_found(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
    ) -> None:
        result = await sql_job_repo.find_by_normalized_url("nonexistent.com/jobs/999")

        assert result is None

    async def test_matches_regardless_of_original_url(
        self,
        sql_job_repo: repos.SqlAlchemyJobRepository,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(
            user_id=user.id,
            url="https://www.EXAMPLE.com/jobs/123?ref=tg",
            normalized_url="example.com/jobs/123",
        )

        result = await sql_job_repo.find_by_normalized_url("example.com/jobs/123")

        assert result is not None
