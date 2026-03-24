import abc
import typing

import weaviate


class BaseWeaviateAsyncDAL(abc.ABC):
    class Meta:
        collection_name: typing.ClassVar[str]

    def __init__(self, client: weaviate.WeaviateAsyncClient, embedding_model: str) -> None:
        self._client = client
        self._embedding_model = embedding_model

    @abc.abstractmethod
    async def ensure_collection(self) -> None:
        raise NotImplementedError
