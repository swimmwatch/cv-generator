import asyncclick as click

from infra.di.container import Container
from utils.logger import setup_logger

from .commands import register


@click.group()
@click.pass_context
async def cli(ctx: click.Context) -> None:
    """Management commands."""
    container = Container()
    container.wire(
        packages=[
            "cli.commands",
        ]
    )

    config = container.config

    setup_logger(
        json_logs=config.logger.json_output(),
        log_level=config.logger.level(),
    )

    container.async_db()  # Initialize the database connection
    container.init_resources()

    async def _shutdown() -> None:
        redis_client = container.redis_client()
        await redis_client.aclose()  # type: ignore[attr-defined]
        await container.shutdown_resources()  # type: ignore[misc]

    ctx.call_on_close(_shutdown)


register(cli)


if __name__ == "__main__":
    cli()
