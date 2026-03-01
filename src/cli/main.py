import asyncclick as click

from infra.di.container import Container
from utils.logger import setup_logger

from .commands import register


@click.group()
async def cli() -> None:
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


register(cli)


if __name__ == "__main__":
    cli()
