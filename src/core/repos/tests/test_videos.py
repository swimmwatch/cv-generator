import pytest

from core import dal
from core import domains
from core import dto
from core import repos


@pytest.mark.asyncio
class TestSqlVideosRepository:
    async def test_bulk_upsert_is_idempotent(
        self,
        sql_video_repo: repos.SqlAlchemyVideoRepository,
    ) -> None:
        data = dto.VideoUpsertDTO(
            source_type="youtube",
            source_pk="abc123",
            title="t1",
        )

        r1 = await sql_video_repo.bulk_upsert_discovered([data])
        assert r1 is not None
        v1 = r1[0]

        r2 = await sql_video_repo.bulk_upsert_discovered([data])
        assert r2 is not None
        v2 = r2[0]

        assert v1.id == v2.id
        assert v2.source_pk == "abc123"
        assert v2.processing_status == domains.VideoProcessingStatus.PENDING

    async def test_bulk_upsert_does_not_change_terminal_status(
        self,
        sql_video_repo: repos.SqlAlchemyVideoRepository,
        sql_video_dal: dal.VideoAsyncDAL,
    ) -> None:
        d = dto.VideoUpsertDTO(
            source_type="youtube",
            source_pk="v1",
            title="initial",
        )
        r = await sql_video_repo.bulk_upsert_discovered([d])
        v = r[0]

        # Manually set to DONE.
        await sql_video_dal.filter(id=v.id).update(processing_status=domains.VideoProcessingStatus.DONE)

        # Try "upsert" with new metadata; status must remain DONE.
        d2 = dto.VideoUpsertDTO(
            source_type="youtube",
            source_pk="v1",
            title="changed",
        )
        r2 = await sql_video_repo.bulk_upsert_discovered([d2])
        v2 = r2[0]
        assert v2 is None
