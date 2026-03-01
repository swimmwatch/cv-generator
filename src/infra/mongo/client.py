from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from infra.logger.utils import get_logger

logger = get_logger(__name__)


class AsyncMongoDatabase:
    def __init__(self, url: str, db_name: str) -> None:
        self._client: AsyncIOMotorClient = AsyncIOMotorClient(url)
        self._db: AsyncIOMotorDatabase = self._client[db_name]
        logger.debug("MongoDB client was created")

    @property
    def client(self) -> AsyncIOMotorClient:
        return self._client

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db

    async def stop(self) -> None:
        self._client.close()
        logger.debug("MongoDB client was closed")
