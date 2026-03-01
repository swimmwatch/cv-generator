from fastapi import FastAPI
from starlette.requests import Request

from infra.logger.utils import get_logger
from utils.errors.http_ import BaseHttpError
from utils.errors.http_ import HttpInternalServerError

logger = get_logger(__name__)


def register_error_handler(app: FastAPI) -> FastAPI:
    @app.exception_handler(BaseHttpError)
    async def base_http_error_handler(_: Request, exc: BaseHttpError):
        return exc.to_response()

    @app.exception_handler(Exception)
    def serve_any_exceptions(_: Request, exc: BaseHttpError):
        logger.exception(exc)
        return HttpInternalServerError().to_response()

    return app
