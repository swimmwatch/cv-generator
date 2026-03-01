import pytest
from mongomock_motor import AsyncMongoMockCollection
from mongomock_motor import AsyncMongoMockDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from core import repos


@pytest.fixture
def sql_user_repo(async_db_session: AsyncSession) -> repos.SqlAlchemyUserRepository:
    return repos.SqlAlchemyUserRepository(async_db_session)


@pytest.fixture
def sql_video_repo(async_db_session: AsyncSession) -> repos.SqlAlchemyVideoRepository:
    return repos.SqlAlchemyVideoRepository(async_db_session)


@pytest.fixture
def mongo_video_metadata_collection(async_mongo_db: AsyncMongoMockDatabase) -> AsyncMongoMockCollection:
    return async_mongo_db["video_metadata"]


@pytest.fixture
def mongo_video_metadata_repo(
    mongo_video_metadata_collection: AsyncMongoMockCollection,
) -> repos.MongoVideoMetadataRepository:
    return repos.MongoVideoMetadataRepository(mongo_video_metadata_collection)
