import typing
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqladmin import Admin
from starlette.types import Lifespan

from apps.api.admin import register_admin_views
from apps.api.routers import register_routes
from core import models
from infra.admin.auth import UserModelType
from infra.admin.auth import UsernamePasswordAdminAuth
from infra.api.errors import register_error_handler
from infra.api.middlewares import DBSessionMiddleware
from infra.api.middlewares import LoggingMiddleware
from infra.api.middlewares import RequestIdMiddleware
from infra.di.container import Container
from infra.logger.utils import get_logger
from utils.logger import setup_logger

logger = get_logger(__name__)


def create_server_app(lifespan_func: Lifespan[FastAPI] | None = None) -> FastAPI:
    container = Container()
    config = container.config

    app = FastAPI(
        title=config.api.title(),
        description=config.api.description(),
        version=config.tag(),
        lifespan=lifespan_func or None,
    )
    app.container = container  # type: ignore[attr-defined]

    app = register_error_handler(app)

    app.add_middleware(
        DBSessionMiddleware,
        container=container,
    )
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    app = register_routes(app)

    return app


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> typing.AsyncGenerator[None, None]:
    container = fastapi_app.container  # type: ignore[attr-defined]
    config = container.config

    setup_logger(
        json_logs=config.logger.json_output(),
        log_level=config.logger.level(),
    )

    # Init Databases
    db = container.async_db()

    # Init admin interface
    auth_backend = UsernamePasswordAdminAuth(
        config.admin.session_secret().get_secret_value(),
        typing.cast(type[UserModelType], models.User),
    )
    admin = Admin(
        fastapi_app,
        db.engine,
        authentication_backend=auth_backend,
        debug=config.debug(),
    )
    register_admin_views(admin)

    try:
        container.wire(
            packages=[
                "apps.api.depends",
                "apps.api.routers",
            ],
        )
        container.init_resources()
        logger.info("DI resources was inited.")

        yield
    finally:
        container.shutdown_resources()
        await db.stop()

        logger.info("Shutdown DI resources.")
