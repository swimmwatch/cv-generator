import typing
import uuid

import sqlalchemy as sa
from pwdlib import PasswordHash
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from infra.logger.utils import get_logger

logger = get_logger(__name__)


@typing.runtime_checkable
class UserModelType(typing.Protocol):
    id: int | str | uuid.UUID
    username: str
    password_hash: str
    is_active: bool
    is_staff: bool


class UsernamePasswordAdminAuth(AuthenticationBackend):
    """
    Simple authentication backend for sqladmin that checks username and password.
    """

    _USER_ID_KEY = "user_id"

    def __init__(
        self,
        secret_key: str,
        user_model: type[UserModelType],
    ):
        super().__init__(secret_key=secret_key)
        self._user_model = user_model
        self._pwd = PasswordHash.recommended()

    async def login(self, request: Request) -> bool:
        db = request.state.db
        form = await request.form()
        username = typing.cast(str | None, form.get("username"))
        username = (username or "").strip()
        password = typing.cast(str | None, form.get("password"))
        password = (password or "").strip()

        if not username or not password:
            logger.debug(f"Invalid username or password: {username}")
            return False

        async with db.session() as session:
            stmt = (
                sa.select(self._user_model)
                .where(self._user_model.username == username)  # type: ignore[arg-type]
                .limit(1)
            )
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()

            if not user:
                logger.debug(f"No such user: {username}. Cannot login.")
                return False

            if not user.is_active:
                logger.debug(f"No such user: {username}. Cannot login.")
                return False

            if not user.is_staff:
                logger.debug("User is not staff. Cannot login.")
                return False

            is_valid_password = self._pwd.verify(password, user.password_hash)
            if not is_valid_password:
                logger.debug(f"Invalid username or password: {username}")
                return False

            request.session.update({self._USER_ID_KEY: str(user.id)})
            return True

    async def authenticate(self, request: Request) -> bool:
        db = request.state.db
        user_id = request.session.get(self._USER_ID_KEY)
        if not user_id:
            logger.debug("Cannot authenticate user due to missing ID")
            return False

        async with db.session() as session:
            stmt = sa.select(self._user_model).where(self._user_model.id == user_id)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            check = bool(user and user.is_active and user.is_staff)

            if check:
                message = "Authenticate success"
            else:
                message = "Authenticate failed"

            logger.debug(message, user_id=user_id)

            return check

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True
