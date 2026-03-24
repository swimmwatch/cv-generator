from itertools import batched

import weaviate.classes.config as wvc
from weaviate.classes.query import Filter

from core import domains
from core import models
from infra.db.utils.dal.async_ import SqlAlchemyAsyncDAL
from infra.logger.utils import get_logger
from infra.weaviate.dal import BaseWeaviateAsyncDAL
from utils.weaviate.errors import WeaviateInsertError

logger = get_logger(__name__)


class JobAsyncDAL(SqlAlchemyAsyncDAL):
    class Meta(SqlAlchemyAsyncDAL.Meta):
        model = models.Job


class JobMetadataDAL(BaseWeaviateAsyncDAL):
    class Meta(BaseWeaviateAsyncDAL.Meta):
        collection_name = "jobs"

    _INSERT_BATCH_SIZE = 50

    _PROPERTIES = [
        wvc.Property(name="job_id", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        wvc.Property(name="user_id", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        wvc.Property(name="section", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        wvc.Property(name="content", data_type=wvc.DataType.TEXT),
    ]

    async def _create_collection(self) -> None:
        await self._client.collections.create(
            name=self.Meta.collection_name,
            vector_config=wvc.Configure.Vectors.text2vec_openai(
                model=self._embedding_model,
            ),
            properties=self._PROPERTIES,
        )
        logger.info("Weaviate collection created.", collection=self.Meta.collection_name)

    async def ensure_collection(self) -> None:
        exists = await self._client.collections.exists(self.Meta.collection_name)
        if not exists:
            await self._create_collection()
            return

        collection = self._client.collections.get(self.Meta.collection_name)
        config = await collection.config.get()

        if not config.vector_config:
            logger.warning(
                "Collection has no vectorizer, recreating.",
                collection=self.Meta.collection_name,
            )
            await self._client.collections.delete(self.Meta.collection_name)
            await self._create_collection()
            return

        existing_props = {p.name for p in config.properties}
        for prop in self._PROPERTIES:
            if prop.name not in existing_props:
                await collection.config.add_property(prop)
                logger.info("Added missing property to Weaviate collection.", prop=prop.name)

    async def delete_by_job_id(self, job_id: str) -> None:
        collection = self._client.collections.get(self.Meta.collection_name)
        await collection.data.delete_many(
            where=Filter.by_property("job_id").equal(job_id),
        )
        logger.info("Deleted old job chunks.", job_id=job_id)

    async def insert_chunks(self, chunks: list[domains.JobChunk]) -> None:
        collection = self._client.collections.get(self.Meta.collection_name)
        for batch in batched(chunks, self._INSERT_BATCH_SIZE):
            objects = [
                {
                    "job_id": chunk.job_id,
                    "user_id": chunk.user_id,
                    "section": chunk.section,
                    "content": chunk.content,
                }
                for chunk in batch
            ]
            result = await collection.data.insert_many(objects)
            if result.errors:
                logger.error("Weaviate insert errors.", errors=result.errors)
                msg = f"Failed to insert {len(result.errors)} chunks into Weaviate"
                raise WeaviateInsertError(msg)

        logger.info("Inserted job chunks.", count=len(chunks))

    async def get_full_text_by_job_id(self, job_id: str) -> str | None:
        collection = self._client.collections.get(self.Meta.collection_name)
        result = await collection.query.fetch_objects(
            filters=Filter.by_property("job_id").equal(job_id) & Filter.by_property("section").equal("full_job"),
            limit=1,
        )
        if result.objects:
            return str(result.objects[0].properties["content"])
        return None

    async def get_chunks_by_job_id(self, job_id: str) -> list[domains.JobChunk]:
        collection = self._client.collections.get(self.Meta.collection_name)
        result = await collection.query.fetch_objects(
            filters=Filter.by_property("job_id").equal(job_id),
            limit=100,
        )
        return [
            domains.JobChunk(
                job_id=str(obj.properties["job_id"]),
                user_id=str(obj.properties["user_id"]),
                section=str(obj.properties["section"]),
                content=str(obj.properties["content"]),
                metadata={
                    "job_id": str(obj.properties["job_id"]),
                    "user_id": str(obj.properties["user_id"]),
                },
            )
            for obj in result.objects
        ]

    async def search_by_text(
        self,
        query: str,
        job_id: str,
        user_id: str,
        limit: int = 10,
    ) -> list[str]:
        collection = self._client.collections.get(self.Meta.collection_name)
        result = await collection.query.near_text(
            query=query,
            filters=Filter.by_property("job_id").equal(job_id) & Filter.by_property("user_id").equal(user_id),
            limit=limit,
        )
        return [str(obj.properties["content"]) for obj in result.objects]

    async def search_by_user(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
    ) -> list[str]:
        collection = self._client.collections.get(self.Meta.collection_name)
        result = await collection.query.near_text(
            query=query,
            filters=Filter.by_property("user_id").equal(user_id),
            limit=limit,
        )
        return [str(obj.properties["content"]) for obj in result.objects]
