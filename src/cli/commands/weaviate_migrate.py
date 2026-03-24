import asyncclick as click
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import repos
from infra.weaviate.client import WeaviateClient


@click.command("weaviate-migrate")
@inject
async def weaviate_migrate(
    weaviate_client: "WeaviateClient" = Provide["weaviate_client"],
    resume_metadata_repo: repos.ResumeMetadataRepository = Provide["weaviate_resume_metadata_repo"],
    job_metadata_repo: repos.JobMetadataRepository = Provide["weaviate_job_metadata_repo"],
):
    click.echo("Applying Weaviate migrations...")
    await weaviate_client.connect()
    try:
        await resume_metadata_repo.ensure_collection()
        await job_metadata_repo.ensure_collection()
        click.echo("Weaviate migrations applied successfully!")
    finally:
        await weaviate_client.close()
