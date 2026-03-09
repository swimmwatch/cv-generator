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

    _PROPERTIES = [
        wvc.Property(name="job_id", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        wvc.Property(name="user_id", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        wvc.Property(name="resume_id", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        wvc.Property(name="section", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        wvc.Property(name="content", data_type=wvc.DataType.TEXT),
    ]

    async def ensure_collection(self) -> None:
        exists = await self._client.collections.exists(self.Meta.collection_name)
        if not exists:
            await self._client.collections.create(
                name=self.Meta.collection_name,
                vector_config=wvc.Configure.Vectors.text2vec_transformers(),
                properties=self._PROPERTIES,
            )
            logger.info("Weaviate collection created.", collection=self.Meta.collection_name)
            return

        collection = self._client.collections.get(self.Meta.collection_name)
        config = await collection.config.get()
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
        objects = [
            {
                "job_id": chunk.job_id,
                "user_id": chunk.user_id,
                "resume_id": chunk.resume_id,
                "section": chunk.section,
                "content": chunk.content,
            }
            for chunk in chunks
        ]
        result = await collection.data.insert_many(objects)
        if result.errors:
            logger.error("Weaviate insert errors.", errors=result.errors)
            msg = f"Failed to insert {len(result.errors)} chunks into Weaviate"
            raise WeaviateInsertError(msg)

        logger.info("Inserted job chunks.", count=len(chunks))
