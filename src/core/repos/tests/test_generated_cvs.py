import uuid

from core import dto
from core import models
from core import repos
from tests.factories import GeneratedCVFactory
from tests.factories import JobFactory
from tests.factories import ResumeFactory
from tests.factories import UserFactory
from utils.pagination import PageSizePagination


class TestSqlAlchemyGeneratedCVRepositoryCreateOne:
    async def test_creates_generated_cv(
        self,
        sql_generated_cv_repo: repos.SqlAlchemyGeneratedCVRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)
        job: models.Job = await job_factory.create_async(user_id=user.id)

        data = dto.GeneratedCVCreateDTO(
            user_id=user.id,
            resume_id=resume.id,
            job_id=job.id,
            object_name="generated_cvs/test.pdf",
            file_name="cv_test.pdf",
        )
        result = await sql_generated_cv_repo.create_one(data)

        assert result.user_id == user.id
        assert result.resume_id == resume.id
        assert result.job_id == job.id
        assert result.object_name == "generated_cvs/test.pdf"
        assert result.file_name == "cv_test.pdf"
        assert result.id is not None


class TestSqlAlchemyGeneratedCVRepositoryGetByPk:
    async def test_returns_generated_cv(
        self,
        sql_generated_cv_repo: repos.SqlAlchemyGeneratedCVRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
        job_factory: JobFactory,
        generated_cv_factory: GeneratedCVFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)
        job: models.Job = await job_factory.create_async(user_id=user.id)
        cv: models.GeneratedCV = await generated_cv_factory.create_async(
            user_id=user.id,
            resume_id=resume.id,
            job_id=job.id,
        )

        result = await sql_generated_cv_repo.get_by_pk(cv.id)

        assert result is not None
        assert result.id == cv.id
        assert result.file_name == cv.file_name

    async def test_returns_none_for_nonexistent_pk(
        self,
        sql_generated_cv_repo: repos.SqlAlchemyGeneratedCVRepository,
    ) -> None:
        result = await sql_generated_cv_repo.get_by_pk(uuid.uuid4())

        assert result is None


class TestSqlAlchemyGeneratedCVRepositoryGetByUserId:
    async def test_returns_user_generated_cvs(
        self,
        sql_generated_cv_repo: repos.SqlAlchemyGeneratedCVRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
        job_factory: JobFactory,
        generated_cv_factory: GeneratedCVFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)
        job: models.Job = await job_factory.create_async(user_id=user.id)
        await generated_cv_factory.create_async(
            user_id=user.id,
            resume_id=resume.id,
            job_id=job.id,
        )
        await generated_cv_factory.create_async(
            user_id=user.id,
            resume_id=resume.id,
            job_id=job.id,
        )

        items, total = await sql_generated_cv_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 2
        assert len(items) == 2

    async def test_returns_empty_for_user_without_generated_cvs(
        self,
        sql_generated_cv_repo: repos.SqlAlchemyGeneratedCVRepository,
    ) -> None:
        items, total = await sql_generated_cv_repo.get_by_user_id(
            user_id=uuid.uuid4(),
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 0
        assert items == []

    async def test_does_not_return_other_users_generated_cvs(
        self,
        sql_generated_cv_repo: repos.SqlAlchemyGeneratedCVRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
        job_factory: JobFactory,
        generated_cv_factory: GeneratedCVFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()
        resume1: models.Resume = await resume_factory.create_async(user_id=user1.id)
        resume2: models.Resume = await resume_factory.create_async(user_id=user2.id)
        job1: models.Job = await job_factory.create_async(user_id=user1.id)
        job2: models.Job = await job_factory.create_async(user_id=user2.id)
        await generated_cv_factory.create_async(
            user_id=user1.id,
            resume_id=resume1.id,
            job_id=job1.id,
        )
        await generated_cv_factory.create_async(
            user_id=user2.id,
            resume_id=resume2.id,
            job_id=job2.id,
        )

        items, total = await sql_generated_cv_repo.get_by_user_id(
            user_id=user1.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].user_id == user1.id

    async def test_paginates_results(
        self,
        sql_generated_cv_repo: repos.SqlAlchemyGeneratedCVRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
        job_factory: JobFactory,
        generated_cv_factory: GeneratedCVFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)
        job: models.Job = await job_factory.create_async(user_id=user.id)
        for _ in range(5):
            await generated_cv_factory.create_async(
                user_id=user.id,
                resume_id=resume.id,
                job_id=job.id,
            )

        items_p1, total = await sql_generated_cv_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=2, page=1),
        )

        assert total == 5
        assert len(items_p1) == 2

        items_p3, _ = await sql_generated_cv_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=2, page=3),
        )

        assert len(items_p3) == 1

    async def test_page_beyond_total_returns_empty(
        self,
        sql_generated_cv_repo: repos.SqlAlchemyGeneratedCVRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
        job_factory: JobFactory,
        generated_cv_factory: GeneratedCVFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)
        job: models.Job = await job_factory.create_async(user_id=user.id)
        await generated_cv_factory.create_async(
            user_id=user.id,
            resume_id=resume.id,
            job_id=job.id,
        )

        items, total = await sql_generated_cv_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=99),
        )

        assert total == 1
        assert items == []
