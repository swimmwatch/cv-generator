import pytest
from mongomock_motor import AsyncMongoMockCollection

from core import repos


@pytest.mark.asyncio
class TestMongoVideoMetadataRepository:
    async def test_upsert_one_creates_document(
        self,
        mongo_video_metadata_repo: repos.MongoVideoMetadataRepository,
        mongo_video_metadata_collection: AsyncMongoMockCollection,
    ) -> None:
        await mongo_video_metadata_repo.upsert_one(
            source_type="youtube",
            source_pk="abc123",
            item={"duration": 120, "tags": ["music"]},
        )

        doc = await mongo_video_metadata_collection.find_one(
            {"source_type": "youtube", "source_pk": "abc123"},
        )
        assert doc is not None
        assert doc["duration"] == 120
        assert doc["tags"] == ["music"]

    async def test_upsert_one_updates_existing_document(
        self,
        mongo_video_metadata_repo: repos.MongoVideoMetadataRepository,
        mongo_video_metadata_collection: AsyncMongoMockCollection,
    ) -> None:
        await mongo_video_metadata_repo.upsert_one(
            source_type="youtube",
            source_pk="abc123",
            item={"duration": 120},
        )

        await mongo_video_metadata_repo.upsert_one(
            source_type="youtube",
            source_pk="abc123",
            item={"duration": 300, "resolution": "1080p"},
        )

        docs = await mongo_video_metadata_collection.find(
            {"source_type": "youtube", "source_pk": "abc123"},
        ).to_list(None)
        assert len(docs) == 1
        assert docs[0]["duration"] == 300
        assert docs[0]["resolution"] == "1080p"

    async def test_upsert_one_different_source_pks(
        self,
        mongo_video_metadata_repo: repos.MongoVideoMetadataRepository,
        mongo_video_metadata_collection: AsyncMongoMockCollection,
    ) -> None:
        await mongo_video_metadata_repo.upsert_one(
            source_type="youtube",
            source_pk="vid1",
            item={"duration": 100},
        )
        await mongo_video_metadata_repo.upsert_one(
            source_type="youtube",
            source_pk="vid2",
            item={"duration": 200},
        )

        count = await mongo_video_metadata_collection.count_documents({})
        assert count == 2
