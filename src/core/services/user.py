from pwdlib import PasswordHash

from core import domains
from core import dto
from core import repos
from infra.logger.utils import get_logger
from utils.iter import compare_changes

logger = get_logger(__name__)


class UserService:
    _TG_USER_CHANGES_FIELDS = (
        "first_name",
        "last_name",
        "language_code",
    )

    def __init__(
        self,
        user_repo: repos.UserRepository,
    ):
        self._user_repo = user_repo
        self._pwd = PasswordHash.recommended()

    async def get_current_user(self, pk: domains.UserID) -> dto.UserOutDTO | None:
        user = await self._user_repo.get_by_pk(pk)
        if not user:
            return None

        return dto.UserOutDTO.from_model(user)

    async def create_superuser(
        self,
        data: dto.UserAdminCreateDTO,
    ) -> dto.UserOutDTO:
        password_hash = self._pwd.hash(data.password)

        user_dto = dto.UserCreateDTO(
            messenger_id=data.messenger_id,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            password_hash=password_hash,
            is_superuser=True,
            is_staff=True,
            language_code=None,
        )
        return await self._user_repo.create_one(user_dto)

    async def update_or_create_by_tg(
        self,
        tg_user: domains.TelegramUserLike,
    ):
        messenger_id = str(tg_user.id)
        db_user = await self._user_repo.get_by_messenger_id(messenger_id)

        new_user_dto = dto.UserCreateDTO(
            messenger_id=messenger_id,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            username=tg_user.username,
            password_hash=None,
            is_superuser=False,
            is_staff=False,
            language_code=tg_user.language_code,
        )

        if db_user is None:
            logger.info("User was not found. Creating new one...")
            new_user = await self._user_repo.create_one(new_user_dto)
            return new_user, True

        logger.info("User was found. Updating...")

        _, changes = compare_changes(
            db_user,
            tg_user,
            self._TG_USER_CHANGES_FIELDS,
        )
        if changes:
            logger.debug("User data was changed. Updating...", changes=changes)

            updated_user = await self._user_repo.update_changes(db_user.id, changes)
            logger.info("User was updated.")
            return updated_user, False
        else:
            logger.debug("User data wasn't changed.")
            return db_user, False

    async def deduct_credits(self, user_id: domains.UserID, action: domains.CreditAction) -> bool:
        result = await self._user_repo.deduct_balance(user_id=user_id, amount=domains.CreditAmount(int(action)))
        return result is not None

    async def topup_credits(self, user_id: domains.UserID, amount: domains.CreditAmount) -> domains.CreditAmount | None:
        return await self._user_repo.topup_balance(user_id=user_id, amount=amount)
