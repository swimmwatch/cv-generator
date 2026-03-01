import typing
from datetime import UTC
from datetime import datetime

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from apps.worker.tasks import search_yt_videos
from core import domains
from core import dto
from core import models
from core.repos.videos import SqlAlchemyVideoRepository
from infra.youtube.client import YouTubeClient
from infra.youtube.client import YouTubeVideoCandidate


class FakeYouTubeClient:
    def __init__(self, candidates: list[YouTubeVideoCandidate]):
        self._candidates = candidates

    async def most_popular(
        self,
        *,
        region_code: str,
        time_window_days: int,
        max_results: int = 50,
    ) -> list[YouTubeVideoCandidate]:
        return list(self._candidates)

    async def search(
        self,
        *,
        region_code: str,
        time_window_days: int,
        queries: list[str] | None = None,
        max_results: int = 50,
    ) -> list[YouTubeVideoCandidate]:
        return list(self._candidates)


@pytest.mark.asyncio
async def test_search_yt_videos_skips_done(async_db_session: AsyncSession) -> None:
    repo = SqlAlchemyVideoRepository(async_db_session)

    # Pre-create a DONE video.
    upserted_list = await repo.bulk_upsert_discovered(
        [dto.VideoUpsertDTO(source_type="youtube", source_pk="done1", title="old")]
    )
    assert upserted_list is not None
    v = upserted_list[0]

    await async_db_session.execute(
        sa.update(models.Video)
        .where(models.Video.id == v.id)
        .values(processing_status=domains.VideoProcessingStatus.DONE)
    )
    await async_db_session.flush()

    candidates = [
        YouTubeVideoCandidate(video_id="new1", title="t", description="d", published_at=datetime.now(UTC)),
        YouTubeVideoCandidate(video_id="done1", title="changed"),
    ]

    youtube_client: YouTubeClient = typing.cast(YouTubeClient, typing.cast(object, FakeYouTubeClient(candidates)))

    out = await search_yt_videos(
        region_code="US",
        time_window_days=7,
        max_results=50,
        youtube_client=youtube_client,
        video_repo=repo,
    )

    assert out == ["new1"]
