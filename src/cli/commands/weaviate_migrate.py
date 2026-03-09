import asyncclick as click
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import dal
from infra.weaviate.client import WeaviateClient


@click.command("weaviate-migrate")
@inject
async def weaviate_migrate(
    weaviate_client: "WeaviateClient" = Provide["weaviate_client"],
    resume_metadata_dal: dal.ResumeMetadataDAL = Provide["resume_metadata_dal"],
    job_metadata_dal: dal.JobMetadataDAL = Provide["job_metadata_dal"],
):
    click.echo("Applying Weaviate migrations...")
    await weaviate_client.connect()
    try:
        await resume_metadata_dal.ensure_collection()
        await job_metadata_dal.ensure_collection()
        click.echo("Weaviate migrations applied successfully!")
    finally:
        await weaviate_client.close()
