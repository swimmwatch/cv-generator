from fastapi import APIRouter
from fastapi import FastAPI

from apps.api.routers.agents import router as agents_router
from apps.api.routers.health import make_health_router
from apps.api.routers.users import router as users_router


def register_routes(app: FastAPI) -> FastAPI:
    container = app.container  # type: ignore[attr-defined]
    api_router = APIRouter(prefix="/api")

    api_router.include_router(
        make_health_router(container),
        prefix="/health",
    )
    api_router.include_router(users_router)
    api_router.include_router(agents_router)

    app.include_router(api_router)

    return app
