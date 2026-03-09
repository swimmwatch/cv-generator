import abc
import typing

import weaviate


class BaseWeaviateAsyncDAL(abc.ABC):
    class Meta:
        collection_name: typing.ClassVar[str]

    def __init__(self, client: weaviate.WeaviateAsyncClient) -> None:
        self._client = client

    @abc.abstractmethod
    async def ensure_collection(self) -> None:
        raise NotImplementedError
