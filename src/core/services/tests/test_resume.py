import uuid
from unittest.mock import AsyncMock

from core import domains
from core import dto
from core import models
from core import services
from tests.factories import ResumeFactory
from tests.factories import UserFactory
from utils.pagination import PageSizePagination


class TestResumeServiceUpload:
    async def test_uploads_file_and_returns_object_name(
        self,
        resume_service: services.ResumeService,
        async_storage: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        file_name = "resume.pdf"
        file_data = b"pdf-content"
        content_type = "application/pdf"

        result = await resume_service.upload(
            user_id=user_id,
            file_name=file_name,
            file_data=file_data,
            content_type=content_type,
        )

        assert result == f"resume/{user_id}/{file_name}"
        async_storage.put_bytes.assert_awaited_once_with(
            f"resume/{user_id}/{file_name}",
            file_data,
            content_type=content_type,
        )


class TestResumeServiceCreateRecord:
    async def test_creates_record(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()

        result = await resume_service.create_record(
            user_id=user.id,
            object_name=f"resume/{user.id}/resume.pdf",
            file_name="resume.pdf",
        )

        assert result.user_id == user.id
        assert result.object_name == f"resume/{user.id}/resume.pdf"
        assert result.file_name == "resume.pdf"
        assert result.status == domains.ResumeProcessingStatus.PENDING
        assert result.id is not None

    async def test_extracts_title_from_filename(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()

        result = await resume_service.create_record(
            user_id=user.id,
            object_name=f"resume/{user.id}/my_resume.pdf",
            file_name="my_resume.pdf",
        )

        assert result.title == "my_resume"

    async def test_uses_full_name_as_title_when_no_extension(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()

        result = await resume_service.create_record(
            user_id=user.id,
            object_name=f"resume/{user.id}/resume_no_ext",
            file_name="resume_no_ext",
        )

        assert result.title == "resume_no_ext"

    async def test_extracts_title_with_multiple_dots(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()

        result = await resume_service.create_record(
            user_id=user.id,
            object_name=f"resume/{user.id}/my.resume.v2.pdf",
            file_name="my.resume.v2.pdf",
        )

        assert result.title == "my.resume.v2"


class TestResumeServiceUpdateRecordStatus:
    async def test_updates_status(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)

        await resume_service.update_record_status(
            resume_id=resume.id,
            status=domains.ResumeProcessingStatus.DONE,
        )

        updated = await resume_service.get_by_pk(resume.id)
        assert updated is not None
        assert updated.status == domains.ResumeProcessingStatus.DONE


class TestResumeServiceUpdateRecordTitle:
    async def test_updates_title(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)

        await resume_service.update_record_title(
            resume_id=resume.id,
            title="New Title",
        )

        updated = await resume_service.get_by_pk(resume.id)
        assert updated is not None
        assert updated.title == "New Title"


class TestResumeServiceGetByPk:
    async def test_returns_resume(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)

        result = await resume_service.get_by_pk(resume.id)

        assert result is not None
        assert result.id == resume.id
        assert result.title == resume.title

    async def test_returns_none_for_nonexistent_pk(
        self,
        resume_service: services.ResumeService,
    ) -> None:
        result = await resume_service.get_by_pk(uuid.uuid4())

        assert result is None


class TestResumeServiceGetUserResumes:
    async def test_returns_user_resumes(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(user_id=user.id)
        await resume_factory.create_async(user_id=user.id)

        items, total = await resume_service.get_user_resumes(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 2
        assert len(items) == 2

    async def test_returns_empty_for_user_without_resumes(
        self,
        resume_service: services.ResumeService,
    ) -> None:
        items, total = await resume_service.get_user_resumes(
            user_id=uuid.uuid4(),
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 0
        assert items == []

    async def test_does_not_return_other_users_resumes(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()
        await resume_factory.create_async(user_id=user1.id)
        await resume_factory.create_async(user_id=user2.id)

        items, total = await resume_service.get_user_resumes(
            user_id=user1.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].user_id == user1.id

    async def test_paginates_results(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        for _ in range(5):
            await resume_factory.create_async(user_id=user.id)

        items, total = await resume_service.get_user_resumes(
            user_id=user.id,
            pagination=PageSizePagination(page_size=2, page=1),
        )

        assert total == 5
        assert len(items) == 2

    async def test_page_beyond_total_returns_empty(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(user_id=user.id)

        items, total = await resume_service.get_user_resumes(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=99),
        )

        assert total == 1
        assert items == []

    async def test_filters_by_status(
        self,
        resume_service: services.ResumeService,
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

        items, total = await resume_service.get_user_resumes(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
            status=domains.ResumeProcessingStatus.DONE,
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].status == domains.ResumeProcessingStatus.DONE

    async def test_returns_all_when_no_status_filter(
        self,
        resume_service: services.ResumeService,
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

        items, total = await resume_service.get_user_resumes(
            user_id=user.id,
            pagination=PageSizePagination(page_size=10, page=1),
        )

        assert total == 2
        assert len(items) == 2


class TestResumeServiceHasDoneResume:
    async def test_returns_true_when_user_has_done_resume(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.DONE,
        )

        result = await resume_service.has_done_resume(user.id)

        assert result is True

    async def test_returns_false_when_user_has_no_resumes(
        self,
        resume_service: services.ResumeService,
    ) -> None:
        result = await resume_service.has_done_resume(uuid.uuid4())

        assert result is False

    async def test_returns_false_when_only_pending_resumes(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        await resume_factory.create_async(
            user_id=user.id,
            status=domains.ResumeProcessingStatus.PENDING,
        )

        result = await resume_service.has_done_resume(user.id)

        assert result is False

    async def test_does_not_count_other_users_resumes(
        self,
        resume_service: services.ResumeService,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user1: models.User = await user_factory.create_async()
        user2: models.User = await user_factory.create_async()
        await resume_factory.create_async(
            user_id=user2.id,
            status=domains.ResumeProcessingStatus.DONE,
        )

        result = await resume_service.has_done_resume(user1.id)

        assert result is False


class TestResumeServiceDelete:
    async def test_deletes_metadata_storage_and_record(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
        async_storage: AsyncMock,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)
        resume_dto = dto.ResumeOutDTO.model_validate(resume)

        await resume_service.delete(resume_dto)

        resume_metadata_repo.delete_by_resume_id.assert_awaited_once_with(resume_dto.id)
        async_storage.delete.assert_awaited_once_with(resume_dto.object_name)
        result = await resume_service.get_by_pk(resume.id)
        assert result is None

    async def test_calls_operations_in_order(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
        async_storage: AsyncMock,
        user_factory: UserFactory,
        resume_factory: ResumeFactory,
    ) -> None:
        user: models.User = await user_factory.create_async()
        resume: models.Resume = await resume_factory.create_async(user_id=user.id)
        resume_dto = dto.ResumeOutDTO.model_validate(resume)

        call_order: list[str] = []
        resume_metadata_repo.delete_by_resume_id.side_effect = lambda *a: call_order.append("metadata")
        async_storage.delete.side_effect = lambda *a, **kw: call_order.append("storage")

        await resume_service.delete(resume_dto)

        assert call_order == ["metadata", "storage"]


class TestResumeServiceDownload:
    async def test_returns_file_bytes(
        self,
        resume_service: services.ResumeService,
        async_storage: AsyncMock,
    ) -> None:
        async_storage.get_bytes.return_value = b"file-content"

        result = await resume_service.download("resume/user/file.pdf")

        assert result == b"file-content"
        async_storage.get_bytes.assert_awaited_once_with("resume/user/file.pdf")


class TestResumeServiceSaveMetadata:
    async def test_ensures_collection_deletes_old_and_inserts_new(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        resume_id = uuid.uuid4()
        chunks = [
            domains.ResumeChunk(
                resume_id=str(resume_id),
                user_id="u1",
                section="full_resume",
                content="text",
                metadata={},
            ),
        ]

        await resume_service.save_metadata(resume_id=resume_id, chunks=chunks)

        resume_metadata_repo.ensure_collection.assert_awaited_once()
        resume_metadata_repo.delete_by_resume_id.assert_awaited_once_with(resume_id)
        resume_metadata_repo.insert_chunks.assert_awaited_once_with(chunks)

    async def test_inserts_provided_chunks(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        resume_id = uuid.uuid4()
        chunks = [
            domains.ResumeChunk(
                resume_id=str(resume_id),
                user_id="u1",
                section="about",
                content="about text",
                metadata={"section": "about"},
            ),
            domains.ResumeChunk(
                resume_id=str(resume_id),
                user_id="u1",
                section="skills",
                content="Python, Go",
                metadata={"section": "skills"},
            ),
        ]

        await resume_service.save_metadata(resume_id=resume_id, chunks=chunks)

        resume_metadata_repo.insert_chunks.assert_awaited_once_with(chunks)


class TestResumeServiceSearchByText:
    async def test_returns_search_results(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        resume_metadata_repo.search_by_text.return_value = ["result1", "result2"]

        result = await resume_service.search_by_text(
            query="python",
            resume_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        assert result == ["result1", "result2"]

    async def test_returns_empty_when_no_results(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        resume_metadata_repo.search_by_text.return_value = []

        result = await resume_service.search_by_text(
            query="nonexistent",
            resume_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        assert result == []

    async def test_passes_correct_arguments(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        resume_id = uuid.uuid4()
        user_id = uuid.uuid4()

        await resume_service.search_by_text(
            query="python",
            resume_id=resume_id,
            user_id=user_id,
            limit=5,
        )

        resume_metadata_repo.search_by_text.assert_awaited_once_with(
            query="python",
            resume_id=resume_id,
            user_id=user_id,
            limit=5,
        )

    async def test_uses_default_limit(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        await resume_service.search_by_text(
            query="python",
            resume_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        call_kwargs = resume_metadata_repo.search_by_text.call_args[1]
        assert call_kwargs["limit"] == 10


class TestResumeServiceSearchByUser:
    async def test_returns_search_results(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        resume_metadata_repo.search_by_user.return_value = ["result1"]

        result = await resume_service.search_by_user(
            query="python",
            user_id=uuid.uuid4(),
        )

        assert result == ["result1"]

    async def test_returns_empty_when_no_results(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        resume_metadata_repo.search_by_user.return_value = []

        result = await resume_service.search_by_user(
            query="nonexistent",
            user_id=uuid.uuid4(),
        )

        assert result == []

    async def test_passes_correct_arguments(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()

        await resume_service.search_by_user(
            query="python",
            user_id=user_id,
            limit=3,
        )

        resume_metadata_repo.search_by_user.assert_awaited_once_with(
            query="python",
            user_id=user_id,
            limit=3,
        )

    async def test_uses_default_limit(
        self,
        resume_service: services.ResumeService,
        resume_metadata_repo: AsyncMock,
    ) -> None:
        await resume_service.search_by_user(
            query="python",
            user_id=uuid.uuid4(),
        )

        call_kwargs = resume_metadata_repo.search_by_user.call_args[1]
        assert call_kwargs["limit"] == 10
