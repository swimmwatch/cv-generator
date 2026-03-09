import weaviate

from infra.logger.utils import get_logger

logger = get_logger(__name__)


class WeaviateClient:
    def __init__(
        self,
        http_host: str,
        http_port: int,
        grpc_host: str,
        grpc_port: int,
    ) -> None:
        self._client = weaviate.use_async_with_custom(
            http_host=http_host,
            http_port=http_port,
            http_secure=False,
            grpc_host=grpc_host,
            grpc_port=grpc_port,
            grpc_secure=False,
        )

    async def connect(self) -> None:
        await self._client.connect()
        logger.info("Weaviate client connected.")

    async def close(self) -> None:
        await self._client.close()
        logger.info("Weaviate client closed.")

    @property
    def client(self) -> weaviate.WeaviateAsyncClient:
        return self._client
