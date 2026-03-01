import typing
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import APIRouter
from fastapi import FastAPI
from starlette.types import Lifespan

from apps.bot.app import create_bot
from apps.bot.app import create_dispatcher
from infra.api.middlewares import DBSessionMiddleware
from infra.api.middlewares import LoggingMiddleware
from infra.api.middlewares import RequestIdMiddleware
from infra.bot.runtime.aiogram import AiogramPoller
from infra.bot.runtime.aiogram import AiogramWebhookServer
from infra.di.container import Container
from infra.logger.utils import get_logger
from utils.config import RunLevelEnum
from utils.logger import setup_logger

logger = get_logger(__name__)


def create_server_app(lifespan_func: Lifespan[FastAPI] | None = None) -> FastAPI:
    container = Container()
    config = container.config

    app = FastAPI(
        title=config.telegram_bot.title(),
        description=config.telegram_bot.description(),
        version=config.tag(),
        lifespan=lifespan_func or None,
    )
    app.container = container  # type: ignore[attr-defined]

    app.add_middleware(
        DBSessionMiddleware,
        container=container,
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    return app


def add_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    app.include_router(api_router)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> typing.AsyncGenerator[None, None]:
    container = fastapi_app.container  # type: ignore[attr-defined]
    config = container.config

    setup_logger(
        json_logs=config.logger.json_output(),
        log_level=config.logger.level(),
    )

    add_routes(fastapi_app)

    # DI must be wired before aiogram starts processing updates.
    db = container.async_db()
    runner = None

    try:
        container.wire(
            packages=[
                "apps.bot",
            ],
        )
        container.init_resources()  # type: ignore[misc]
        logger.info("DI resources was inited.")

        bot = create_bot(container)
        dp = create_dispatcher(container)

        match config.env():
            case RunLevelEnum.LOCAL | RunLevelEnum.DEVELOPMENT:
                runner = AiogramPoller(bot, dp)
            case RunLevelEnum.PRODUCTION:
                runner = AiogramWebhookServer(
                    bot,
                    dp,
                    fastapi_app,
                    config.telegram_bot.webhook_url(),
                    config.telegram_bot.webhook_secret_token().get_secret_value(),
                )
            case _:
                logger.error(f"Unsupported run level: {config.env()}")
                typing.assert_never(config.env())

        await runner.start()

        yield
    finally:
        if runner is not None:
            with suppress(Exception):
                await runner.stop()

        container.shutdown_resources()  # type: ignore[misc]
        await db.stop()

        logger.info("Shutdown DI resources.")
