import typing

from motor.motor_asyncio import AsyncIOMotorCollection
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core import dal
from core import domains
from core import dto
from core import models


class VideoRepository(typing.Protocol):
    async def bulk_upsert_discovered(
        self,
        items: list[dto.VideoUpsertDTO],
    ) -> list[dto.VideoOutDTO | None]:
        """Bulk upsert by (source_type, source_pk).

        Returns list of videos in the same order as input items,
        or None if the operation couldn't be completed.

        If the video is created, its status must be `pending`.
        If it already exists, this method must not change terminal statuses.
        """

    async def get_by_source(
        self,
        source_type: str,
        source_pk: str,
    ) -> dto.VideoOutDTO | None:
        pass


class SqlAlchemyVideoRepository(VideoRepository):
    def __init__(self, session: AsyncSession):
        self._session = session
        self._video_dal = dal.VideoAsyncDAL(session)

    async def get_by_source(
        self,
        source_type: str,
        source_pk: str,
    ) -> dto.VideoOutDTO | None:
        video = await self._video_dal.filter(source_type=source_type, source_pk=source_pk).first()
        if not video:
            return None
        return dto.VideoOutDTO.from_model(video)

    async def bulk_upsert_discovered(
        self,
        items: list[dto.VideoUpsertDTO],
    ) -> list[dto.VideoOutDTO | None]:
        if not items:
            return []

        # De-duplicate within this call (keep first occurrence order).
        unique_by_key: dict[tuple[str, str], dto.VideoUpsertDTO] = {}
        for it in items:
            unique_by_key.setdefault((it.source_type, it.source_pk), it)

        rows: list[dict[str, typing.Any]] = [
            {
                "source_type": it.source_type,
                "source_pk": it.source_pk,
                "title": it.title,
                "description": it.description,
                "published_at": it.published_at,
                "processing_status": domains.VideoProcessingStatus.PENDING,
                "reject_reason_codes": [],
                "views": 0,
                "likes": 0,
                "comments": 0,
            }
            for it in unique_by_key.values()
        ]

        stmt = pg_insert(models.Video).values(rows)

        # Update only for non-terminal statuses.
        excluded = stmt.excluded
        terminal_statuses = (
            domains.VideoProcessingStatus.REJECTED,
            domains.VideoProcessingStatus.DONE,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[
                models.Video.source_type,
                models.Video.source_pk,
            ],
            set_={
                "title": excluded.title,
                "description": excluded.description,
                "published_at": excluded.published_at,
            },
            where=models.Video.processing_status.notin_(terminal_statuses),
        ).returning(models.Video)

        res = await self._session.execute(stmt)
        returned = res.scalars().all()

        by_key: dict[tuple[str, str], dto.VideoOutDTO] = {
            (v.source_type, v.source_pk): dto.VideoOutDTO.from_model(v) for v in returned
        }
        return [by_key.get((it.source_type, it.source_pk)) for it in items]


class VideoMetadataRepository(typing.Protocol):
    async def upsert_one(
        self,
        source_type: str,
        source_pk: str,
        item: dict[str, typing.Any],
    ) -> None:
        """Create or update video metadata by (source_type, source_pk)."""
        pass


class MongoVideoMetadataRepository(VideoMetadataRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def upsert_one(
        self,
        source_type: str,
        source_pk: str,
        item: dict[str, typing.Any],
    ) -> None:
        filter_ = {"source_type": source_type, "source_pk": source_pk}
        await self._collection.replace_one(
            filter_,
            {**filter_, **item},
            upsert=True,
        )
