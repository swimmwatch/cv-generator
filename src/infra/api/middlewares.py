import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from infra.db.client import AsyncDatabase
from infra.db.session_scope import clear_session_scope
from infra.db.session_scope import set_session_scope
from infra.di.container import Container
from infra.logger.utils import get_logger

logger = get_logger(__name__)


class DBSessionMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to ensure one SQLAlchemy async session per HTTP request.

    - Binds a ContextVar-based scope key for the duration of the request.
    - Commits on success, rolls back on error.
    - Clears the scoped session at the end.
    """

    def __init__(self, app: ASGIApp, container: Container) -> None:
        super().__init__(app)
        self._container = container
        self._db: AsyncDatabase = container.async_db()

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request.state.db = self._db

        scope_key = getattr(request.state, "request_id", None)  # Ensure this is set by RequestIdMiddleware
        set_session_scope(scope_key)

        try:
            response = await call_next(request)
            await self._db.commit_scoped_session()
            return response
        except Exception as err:
            logger.exception(err)

            await self._db.rollback_scoped_session()
            raise
        finally:
            clear_session_scope()
            await self._db.remove_scoped_session()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure each request has a unique ID for tracing."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if not hasattr(request.state, "request_id"):
            request_id = str(uuid.uuid4())
            logger.debug(f"Assigned new request ID: {request_id}")
        else:
            request_id = request.state.request_id
            logger.debug(f"Request already has ID: {request_id}")

        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = getattr(request.state, "request_id", None)  # Ensure this is set by RequestIdMiddleware
        start_time = time.perf_counter_ns()

        query = request.url.query
        url = request.url.path + ("?" + query if query else "")
        http_method = request.method
        http_version = request.scope["http_version"]

        if request.client is None:
            logger.warning("Request client information is missing")
            client_addr = "unknown"
        else:
            client_host = request.client.host
            client_port = request.client.port
            client_addr = f"{client_host}:{client_port}"

        log = f"{http_method} {url}"

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            addr=client_addr,
        )

        logger.info(
            log,
            mode="started",
            request_id=request_id,
            addr=client_addr,
            http_version=http_version,
        )

        response = await call_next(request)

        process_time_float = time.perf_counter_ns() - start_time
        process_time = str(process_time_float / 10**9)
        status_code = str(response.status_code)

        user = getattr(request.state, "user", None)
        user_id = user.id if user else None

        logger.info(
            log,
            mode="finished",
            request_id=request_id,
            addr=client_addr,
            code=status_code,
            http_version=http_version,
            duration=process_time,
            user_id=str(user_id),
        )

        response.headers["X-Process-Time"] = process_time

        structlog.contextvars.clear_contextvars()

        return response
