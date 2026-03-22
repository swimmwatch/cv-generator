import uuid
from unittest.mock import AsyncMock

import pytest

from core import domains
from core import dto
from core import models
from core import services
from tests.factories import JobFactory
from tests.factories import UserFactory
from utils.pagination import PageSizePagination


class TestJobServiceGetByPk:
    async def test_returns_job(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        job: models.Job = await job_factory.create_async(user_id=user.id)

        result = await job_service.get_by_pk(job.id)

        assert result is not None
        assert result.id == job.id
        assert result.title == job.title

    async def test_returns_none_for_nonexistent_pk(
        self,
        job_service: services.JobService,
    ) -> None:
        result = await job_service.get_by_pk(uuid.uuid4())

        assert result is None


class TestJobServiceGetUserJobs:
    async def test_returns_user_jobs(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user.id)
        await job_factory.create_async(user_id=user.id)

        items, total = await job_service.get_user_jobs(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 2
        assert len(items) == 2

    async def test_returns_empty_for_user_without_jobs(
        self,
        job_service: services.JobService,
    ) -> None:
        items, total = await job_service.get_user_jobs(
            user_id=uuid.uuid4(),
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 0
        assert items == []

    async def test_does_not_return_other_users_jobs(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user1.id)
        await job_factory.create_async(user_id=user2.id)

        items, total = await job_service.get_user_jobs(
            user_id=user1.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].user_id == user1.id

    async def test_paginates_results(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        for _ in range(5):
            await job_factory.create_async(user_id=user.id)

        items, total = await job_service.get_user_jobs(
            user_id=user.id,
            pagination=PageSizePagination(page_size=2, page=1),
        )

        assert total == 5
        assert len(items) == 2

    async def test_page_beyond_total_returns_empty(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user.id)

        items, total = await job_service.get_user_jobs(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=99),
        )

        assert total == 1
        assert items == []


class TestJobServiceHasJobs:
    async def test_returns_true_when_user_has_jobs(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user.id)

        result = await job_service.has_jobs(user.id)

        assert result is True

    async def test_returns_false_when_user_has_no_jobs(
        self,
        job_service: services.JobService,
    ) -> None:
        result = await job_service.has_jobs(uuid.uuid4())

        assert result is False

    async def test_does_not_count_other_users_jobs(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()
        await job_factory.create_async(user_id=user2.id)

        result = await job_service.has_jobs(user1.id)

        assert result is False


class TestJobServiceDelete:
    async def test_deletes_metadata_and_record(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        job: models.Job = await job_factory.create_async(user_id=user.id)
        job_dto = dto.JobOutDTO.model_validate(job)

        await job_service.delete(job_dto)

        job_metadata_repo.delete_by_job_id.assert_awaited_once_with(job_dto.id)
        result = await job_service.get_by_pk(job.id)
        assert result is None

    async def test_calls_operations_in_order(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
        user_factory: UserFactory,
        job_factory: JobFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        job: models.Job = await job_factory.create_async(user_id=user.id)
        job_dto = dto.JobOutDTO.model_validate(job)

        call_order: list[str] = []
        job_metadata_repo.delete_by_job_id.side_effect = lambda *a: call_order.append("metadata")

        await job_service.delete(job_dto)

        assert call_order[0] == "metadata"


class TestJobServiceCreateRecord:
    async def test_creates_job(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()

        result = await job_service.create_record(
            user_id=user.id,
            title="Software Engineer",
            url="https://example.com/job/1",
        )

        assert result.user_id == user.id
        assert result.title == "Software Engineer"
        assert result.url == "https://example.com/job/1"
        assert result.normalized_url == "example.com/job/1"
        assert result.id is not None

    async def test_creates_job_with_metadata(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        metadata = {"skills": ["python", "sql"]}

        result = await job_service.create_record(
            user_id=user.id,
            title="Backend Dev",
            url="https://example.com/job/2",
            metadata_=metadata,
        )

        assert result.metadata_ == metadata

    async def test_creates_job_without_metadata(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()

        result = await job_service.create_record(
            user_id=user.id,
            title="DevOps",
            url="https://example.com/job/3",
        )

        assert result.metadata_ is None


class TestJobServiceSaveMetadata:
    async def test_deletes_old_and_inserts_new_chunks(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_id = uuid.uuid4()
        chunks = [
            domains.JobChunk(
                job_id=str(job_id),
                user_id="user-1",
                section="full_job",
                content="Some job description",
                metadata={"job_id": str(job_id), "user_id": "user-1"},
            ),
        ]

        result = await job_service.save_metadata(
            job_id=job_id,
            chunks=chunks,
        )

        job_metadata_repo.delete_by_job_id.assert_awaited_once_with(job_id)
        job_metadata_repo.insert_chunks.assert_awaited_once_with(chunks)
        assert result == chunks

    async def test_returns_chunks_as_passed(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_id = uuid.uuid4()
        user_id = uuid.uuid4()
        chunks = [
            domains.JobChunk(
                job_id=str(job_id),
                user_id=str(user_id),
                section="full_job",
                content="Job text content",
                metadata={"job_id": str(job_id), "user_id": str(user_id)},
            ),
            domains.JobChunk(
                job_id=str(job_id),
                user_id=str(user_id),
                section="summary",
                content="A summary",
                metadata={"job_id": str(job_id), "user_id": str(user_id), "section": "summary"},
            ),
        ]

        result = await job_service.save_metadata(
            job_id=job_id,
            chunks=chunks,
        )

        assert result == chunks
        for chunk in result:
            assert chunk.job_id == str(job_id)
            assert chunk.user_id == str(user_id)

    async def test_ensures_collection(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        await job_service.save_metadata(
            job_id=uuid.uuid4(),
            chunks=[],
        )

        job_metadata_repo.ensure_collection.assert_awaited_once()

    async def test_inserts_same_chunks_returned(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_id = uuid.uuid4()
        chunks = [
            domains.JobChunk(
                job_id=str(job_id),
                user_id="user-1",
                section="full_job",
                content="Description here",
                metadata={"job_id": str(job_id), "user_id": "user-1"},
            ),
        ]

        result = await job_service.save_metadata(
            job_id=job_id,
            chunks=chunks,
        )

        inserted_chunks = job_metadata_repo.insert_chunks.call_args[0][0]
        assert inserted_chunks == result


class TestJobServiceGetFullText:
    async def test_returns_text(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_metadata_repo.get_full_text_by_job_id.return_value = "Full job text"

        result = await job_service.get_full_text(uuid.uuid4())

        assert result == "Full job text"

    async def test_returns_none_when_not_found(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_metadata_repo.get_full_text_by_job_id.return_value = None

        result = await job_service.get_full_text(uuid.uuid4())

        assert result is None

    async def test_passes_correct_job_id(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_id = uuid.uuid4()

        await job_service.get_full_text(job_id)

        job_metadata_repo.get_full_text_by_job_id.assert_awaited_once_with(job_id)


class TestJobServiceSearchByText:
    async def test_returns_search_results(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_metadata_repo.search_by_text.return_value = ["result1", "result2"]

        result = await job_service.search_by_text(
            query="python",
            job_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        assert result == ["result1", "result2"]

    async def test_returns_empty_when_no_results(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_metadata_repo.search_by_text.return_value = []

        result = await job_service.search_by_text(
            query="nonexistent",
            job_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        assert result == []

    async def test_passes_correct_arguments(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await job_service.search_by_text(
            query="python",
            job_id=job_id,
            user_id=user_id,
            limit=5,
        )

        job_metadata_repo.search_by_text.assert_awaited_once_with(
            query="python",
            job_id=job_id,
            user_id=user_id,
            limit=5,
        )

    async def test_uses_default_limit(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        await job_service.search_by_text(
            query="python",
            job_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        call_kwargs = job_metadata_repo.search_by_text.call_args[1]
        assert call_kwargs["limit"] == 10


class TestJobServiceSearchByUser:
    async def test_returns_search_results(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_metadata_repo.search_by_user.return_value = ["result1"]

        result = await job_service.search_by_user(
            query="python",
            user_id=uuid.uuid4(),
        )

        assert result == ["result1"]

    async def test_returns_empty_when_no_results(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        job_metadata_repo.search_by_user.return_value = []

        result = await job_service.search_by_user(
            query="nonexistent",
            user_id=uuid.uuid4(),
        )

        assert result == []

    async def test_passes_correct_arguments(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()

        await job_service.search_by_user(
            query="python",
            user_id=user_id,
            limit=3,
        )

        job_metadata_repo.search_by_user.assert_awaited_once_with(
            query="python",
            user_id=user_id,
            limit=3,
        )

    async def test_uses_default_limit(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
    ) -> None:
        await job_service.search_by_user(
            query="python",
            user_id=uuid.uuid4(),
        )

        call_kwargs = job_metadata_repo.search_by_user.call_args[1]
        assert call_kwargs["limit"] == 10


class TestJobServiceFindExistingJob:
    async def test_returns_job_when_normalized_url_matches(
        self,
        job_service: services.JobService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await job_service.create_record(
            user_id=user.id,
            title="Dev",
            url="https://www.example.com/jobs/42?ref=tg",
        )

        result = await job_service.find_existing_job("https://example.com/jobs/42")

        assert result is not None
        assert result.title == "Dev"

    async def test_returns_none_when_no_match(
        self,
        job_service: services.JobService,
    ) -> None:
        result = await job_service.find_existing_job("https://example.com/nonexistent")

        assert result is None


class TestJobServiceCopyJobForUser:
    async def test_copies_job_with_metadata(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
        user_factory: UserFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()

        source = await job_service.create_record(
            user_id=user1.id,
            title="Senior Dev",
            url="https://example.com/jobs/1",
            metadata_={"skills": ["python"]},
        )
        source_chunks = [
            domains.JobChunk(
                job_id=str(source.id),
                user_id=str(user1.id),
                section="full_job",
                content="Full job text",
                metadata={"job_id": str(source.id), "user_id": str(user1.id)},
            ),
        ]
        job_metadata_repo.get_chunks_by_job_id.return_value = source_chunks

        new_job = await job_service.copy_job_for_user(
            source_job=source,
            user_id=user2.id,
            url="https://example.com/jobs/1?ref=copy",
        )

        assert new_job.id != source.id
        assert new_job.user_id == user2.id
        assert new_job.title == "Senior Dev"
        assert new_job.metadata_ == {"skills": ["python"]}
        job_metadata_repo.get_chunks_by_job_id.assert_awaited_once_with(source.id)
        job_metadata_repo.insert_chunks.assert_awaited_once()

    async def test_copies_without_metadata_when_no_chunks(
        self,
        job_service: services.JobService,
        job_metadata_repo: AsyncMock,
        user_factory: UserFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()

        source = await job_service.create_record(
            user_id=user1.id,
            title="Dev",
            url="https://example.com/jobs/2",
        )
        job_metadata_repo.get_chunks_by_job_id.return_value = []

        new_job = await job_service.copy_job_for_user(
            source_job=source,
            user_id=user2.id,
            url="https://example.com/jobs/2",
        )

        assert new_job.user_id == user2.id
        job_metadata_repo.insert_chunks.assert_not_awaited()


class TestJobServiceNormalizeUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://example.com/jobs/123", "example.com/jobs/123"),
            ("http://example.com/jobs/123", "example.com/jobs/123"),
            ("https://www.example.com/jobs/123", "example.com/jobs/123"),
            ("https://WWW.EXAMPLE.COM/Jobs/123", "example.com/Jobs/123"),
            ("https://example.com/jobs/123/", "example.com/jobs/123"),
            ("https://example.com/jobs/123?ref=tg&src=bot", "example.com/jobs/123"),
            ("https://example.com/jobs/123#section", "example.com/jobs/123"),
            ("https://example.com/jobs/123?q=1#s", "example.com/jobs/123"),
            ("https://example.com", "example.com"),
            ("https://example.com/", "example.com"),
            ("https://sub.example.com/path", "sub.example.com/path"),
        ],
    )
    def test_normalizes_url(self, url: str, expected: str) -> None:
        assert services.JobService.normalize_url(url) == expected
