import typing

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from fastapi.security import APIKeyHeader
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer
from starlette.requests import Request

from core import domains
from core import services
from infra.logger.utils import get_logger
from utils.depends.auth import BaseAuthProbe

logger = get_logger(__name__)


class DebugAuthProbe(BaseAuthProbe[str]):
    """Debug auth probe. Expects header in format: 'User-ID <user_id>'."""

    schema = APIKeyHeader(
        name="Authorization",
        description="Debug scheme: 'User-ID <user_id>'",
        scheme_name="DebugAuth",
        auto_error=False,
    )

    @inject
    async def authenticate(  # type: ignore[override]
        self,
        request: Request,
        key: str | None = None,
        user_service: "services.UserService" = Provide["user_service"],
    ) -> typing.Any | None:
        if key is None:
            logger.debug("No Authorization header provided")
            return None

        parsed_key = self._parse_key(key)
        if parsed_key is None:
            logger.debug(f"No valid key found in header: {key}")
            return None

        user_pk = domains.UserID(parsed_key)
        return await user_service.get_current_user(user_pk)

    @staticmethod
    def _parse_key(value: str) -> str | None:
        parts = value.strip().split()
        if len(parts) == 2 and parts[0] == "User-ID" and parts[1]:
            return parts[1]
        return None


class JwtAuthProbe(BaseAuthProbe[HTTPAuthorizationCredentials]):
    """JWT auth probe."""

    schema = HTTPBearer(
        description="JWT scheme",
        scheme_name="JWTAuth",
        auto_error=False,
    )

    async def authenticate(
        self,
        request: Request,
        key: HTTPAuthorizationCredentials | None = None,
    ) -> typing.Any | None:
        # TODO: implement JWT auth probe
        return None
