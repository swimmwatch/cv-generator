import uuid

from core import domains
from core import dto
from core import models
from core import repos
from tests.factories import ResumeFactory
from tests.factories import UserFactory
from utils.pagination import PageSizePagination


class TestSqlAlchemyResumeRepositoryCreateOne:
    async def test_creates_resume(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.ResumeCreateDTO(
            user_id=user.id,
            object_name="resumes/test.pdf",
            file_name="test.pdf",
        )
        result = await sql_resume_repo.create_one(data)

        assert result.user_id == user.id
        assert result.object_name == "resumes/test.pdf"
        assert result.file_name == "test.pdf"
        assert result.status == domains.ResumeProcessingStatus.PENDING
        assert result.title is None
        assert result.id is not None

    async def test_creates_resume_with_title(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.ResumeCreateDTO(
            user_id=user.id,
            title="My Resume",
            object_name="resumes/my.pdf",
            file_name="my.pdf",
        )
        result = await sql_resume_repo.create_one(data)

        assert result.title == "My Resume"

    async def test_creates_resume_with_custom_status(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        data = dto.ResumeCreateDTO(
            user_id=user.id,
            object_name="resumes/done.pdf",
            file_name="done.pdf",
            status=domains.ResumeProcessingStatus.DONE,
        )
        result = await sql_resume_repo.create_one(data)

        assert result.status == domains.ResumeProcessingStatus.DONE


class TestSqlAlchemyResumeRepositoryGetByPk:
    async def test_returns_resume(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)

        result = await sql_resume_repo.get_by_pk(resume.id)

        assert result is not None
        assert result.id == resume.id
        assert result.file_name == resume.file_name

    async def test_returns_none_for_nonexistent_pk(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
    ) -> None:
        result = await sql_resume_repo.get_by_pk(uuid.uuid4())

        assert result is None


class TestSqlAlchemyResumeRepositoryGetByUserId:
    async def test_returns_user_resumes(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(user_id=user.id)
        await resume_factory.create_async(user_id=user.id)

        items, total = await sql_resume_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 2
        assert len(items) == 2

    async def test_returns_empty_for_user_without_resumes(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
    ) -> None:
        items, total = await sql_resume_repo.get_by_user_id(
            user_id=uuid.uuid4(),
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 0
        assert items == []

    async def test_does_not_return_other_users_resumes(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()
        await resume_factory.create_async(user_id=user1.id)
        await resume_factory.create_async(user_id=user2.id)

        items, total = await sql_resume_repo.get_by_user_id(
            user_id=user1.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].user_id == user1.id

    async def test_filters_by_status(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.DONE,
        )
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.PENDING,
        )

        items, total = await sql_resume_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
            status=domains.ResumeProcessingStatus.DONE,
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].status == domains.ResumeProcessingStatus.DONE

    async def test_paginates_results(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        for _ in range(5):
            await resume_factory.create_async(user_id=user.id)

        items_p1, total = await sql_resume_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=2, page=1),
        )

        assert total == 5
        assert len(items_p1) == 2

        items_p3, _ = await sql_resume_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=2, page=3),
        )

        assert len(items_p3) == 1

    async def test_page_beyond_total_returns_empty(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(user_id=user.id)

        items, total = await sql_resume_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=99),
        )

        assert total == 1
        assert items == []

    async def test_status_none_returns_all(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.DONE,
        )
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.PENDING,
        )
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.PROCESSING,
        )

        items, total = await sql_resume_repo.get_by_user_id(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
            status=None,
        )

        assert total == 3
        assert len(items) == 3


class TestSqlAlchemyResumeRepositoryHasDoneResume:
    async def test_returns_true_when_done_resume_exists(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.DONE,
        )

        assert await sql_resume_repo.has_done_resume(user.id) is True

    async def test_returns_false_when_no_done_resume(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.PENDING,
        )

        assert await sql_resume_repo.has_done_resume(user.id) is False

    async def test_returns_false_for_user_without_resumes(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
    ) -> None:
        assert await sql_resume_repo.has_done_resume(uuid.uuid4()) is False


class TestSqlAlchemyResumeRepositoryUpdateStatus:
    async def test_updates_status(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.PENDING,
        )

        await sql_resume_repo.update_status(resume.id, domains.ResumeProcessingStatus.DONE)

        result = await sql_resume_repo.get_by_pk(resume.id)
        assert result is not None
        assert result.status == domains.ResumeProcessingStatus.DONE


class TestSqlAlchemyResumeRepositoryUpdateTitle:
    async def test_updates_title(
        self,
        sql_resume_repo: repos.SqlAlchemyResumeRepository,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(
            user_id=user.id,
            title=None,
        )

        await sql_resume_repo.update_title(resume.id, "New Title")

        result = await sql_resume_repo.get_by_pk(resume.id)
        assert result is not None
        assert result.title == "New Title"
