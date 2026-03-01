import typing

from fastapi import APIRouter
from fastapi import Depends

from apps.api.depends.auth import DebugAuthProbe
from apps.api.depends.auth import JwtAuthProbe
from apps.api.schemas.users import GetCurrentUserOut
from core import dto
from utils.depends.auth import GetCurrentUserProvider
from utils.errors.http_ import HttpUnauthorizedError

router = APIRouter(prefix="/users", tags=["Users"])

auth = GetCurrentUserProvider(
    [
        JwtAuthProbe(),
        DebugAuthProbe(),
    ],
    on_failure=HttpUnauthorizedError,
)
auth_depends = Depends(auth.dependency())
CurrentUser = typing.Annotated[
    dto.UserOutDTO,
    auth_depends,
]


@router.get(
    "/me",
    name="get_current_user",
)
async def get_current_user(user: CurrentUser) -> GetCurrentUserOut:
    """Get current user."""
    return GetCurrentUserOut.from_dto(user)
