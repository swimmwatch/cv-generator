import weaviate.classes.config as wvc
from weaviate.classes.query import Filter

from core import domains
from core import models
from infra.db.utils.dal.async_ import SqlAlchemyAsyncDAL
from infra.logger.utils import get_logger
from infra.weaviate.dal import BaseWeaviateAsyncDAL
from utils.weaviate.errors import WeaviateInsertError

logger = get_logger(__name__)


class ResumeAsyncDAL(SqlAlchemyAsyncDAL):
    class Meta(SqlAlchemyAsyncDAL.Meta):
        model = models.Resume


class ResumeMetadataDAL(BaseWeaviateAsyncDAL):
    class Meta(BaseWeaviateAsyncDAL.Meta):
        collection_name = "resumes"

    async def ensure_collection(self) -> None:
        exists = await self._client.collections.exists(self.Meta.collection_name)
        if not exists:
            await self._client.collections.create(
                name=self.Meta.collection_name,
                vector_config=wvc.Configure.Vectors.text2vec_transformers(),
                properties=[
                    wvc.Property(
                        name="resume_id",
                        data_type=wvc.DataType.TEXT,
                        skip_vectorization=True,
                    ),
                    wvc.Property(
                        name="user_id",
                        data_type=wvc.DataType.TEXT,
                        skip_vectorization=True,
                    ),
                    wvc.Property(
                        name="section",
                        data_type=wvc.DataType.TEXT,
                        skip_vectorization=True,
                    ),
                    wvc.Property(
                        name="content",
                        data_type=wvc.DataType.TEXT,
                    ),
                    wvc.Property(
                        name="first_name",
                        data_type=wvc.DataType.TEXT,
                        skip_vectorization=True,
                    ),
                    wvc.Property(
                        name="last_name",
                        data_type=wvc.DataType.TEXT,
                        skip_vectorization=True,
                    ),
                ],
            )
            logger.info("Weaviate collection created.", collection=self.Meta.collection_name)
            return

        collection = self._client.collections.get(self.Meta.collection_name)
        config = await collection.config.get()
        existing_props = {p.name for p in config.properties}

        missing = [
            wvc.Property(name="resume_id", data_type=wvc.DataType.TEXT, skip_vectorization=True),
            wvc.Property(name="user_id", data_type=wvc.DataType.TEXT, skip_vectorization=True),
            wvc.Property(name="section", data_type=wvc.DataType.TEXT, skip_vectorization=True),
            wvc.Property(name="content", data_type=wvc.DataType.TEXT),
            wvc.Property(name="first_name", data_type=wvc.DataType.TEXT, skip_vectorization=True),
            wvc.Property(name="last_name", data_type=wvc.DataType.TEXT, skip_vectorization=True),
        ]

        for prop in missing:
            if prop.name not in existing_props:
                await collection.config.add_property(prop)
                logger.info("Added missing property to Weaviate collection.", prop=prop.name)

    async def delete_by_resume_id(self, resume_id: str) -> None:
        collection = self._client.collections.get(self.Meta.collection_name)
        await collection.data.delete_many(
            where=Filter.by_property("resume_id").equal(resume_id),
        )
        logger.info("Deleted old resume chunks.", resume_id=resume_id)

    async def delete_by_user_id(self, user_id: str) -> None:
        collection = self._client.collections.get(self.Meta.collection_name)
        await collection.data.delete_many(
            where=Filter.by_property("user_id").equal(user_id),
        )
        logger.info("Deleted old resume chunks.", user_id=user_id)

    async def insert_chunks(self, chunks: list[domains.ResumeChunk]) -> None:
        collection = self._client.collections.get(self.Meta.collection_name)
        objects = [
            {
                "resume_id": chunk.resume_id,
                "user_id": chunk.user_id,
                "section": chunk.section,
                "content": chunk.content,
                "first_name": chunk.metadata.get("first_name", ""),
                "last_name": chunk.metadata.get("last_name", ""),
            }
            for chunk in chunks
        ]
        result = await collection.data.insert_many(objects)
        if result.errors:
            logger.error("Weaviate insert errors.", errors=result.errors)
            msg = f"Failed to insert {len(result.errors)} chunks into Weaviate"
            raise WeaviateInsertError(msg)

        logger.info("Inserted resume chunks.", count=len(chunks))

    async def search_by_text(
        self,
        query: str,
        resume_id: str,
        limit: int = 10,
    ) -> list[str]:
        collection = self._client.collections.get(self.Meta.collection_name)
        result = await collection.query.near_text(
            query=query,
            filters=Filter.by_property("resume_id").equal(resume_id),
            limit=limit,
        )
        return [str(obj.properties["content"]) for obj in result.objects]
