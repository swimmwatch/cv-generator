import pickle  # noqa: S403
import typing
from copy import deepcopy

import structlog
from redis.asyncio import Redis
from telegram.ext import BasePersistence
from telegram.ext import ContextTypes
from telegram.ext import PersistenceInput
from telegram.ext._utils.types import BD
from telegram.ext._utils.types import CD
from telegram.ext._utils.types import UD
from telegram.ext._utils.types import CDCData
from telegram.ext._utils.types import ConversationDict
from telegram.ext._utils.types import ConversationKey

logger = structlog.get_logger(__name__)


class RedisPersistence(BasePersistence):
    __PERSISTENCE_KEY = "telegram_persistence_data"

    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        on_flush: bool = False,
        update_interval: float = 60,
        store_data: PersistenceInput | None = None,
        context_types: ContextTypes[typing.Any, UD, CD, BD] | None = None,
    ) -> None:
        super().__init__(store_data=store_data, update_interval=update_interval)

        self._redis = Redis(host=host, port=port, db=db)
        self.on_flush = on_flush
        self.user_data: dict[int, UD] | None = None
        self.chat_data: dict[int, CD] | None = None
        self.bot_data: BD | None = None
        self.callback_data: CDCData | None = None
        self.conversations: dict[str, dict[tuple[int | str, ...], object]] | None = None
        self.context_types: ContextTypes[typing.Any, UD, CD, BD] = typing.cast(
            ContextTypes[typing.Any, UD, CD, BD],
            context_types or ContextTypes(),
        )

    async def _load_data(self):
        logger.debug("Loading persistence data...")

        data_bytes = await self._redis.get(self.__PERSISTENCE_KEY)
        data = data_bytes if data_bytes is not None else pickle.dumps({})
        serialized_data = typing.cast(dict[str, typing.Any], pickle.loads(data))  # noqa: S301

        self.user_data = serialized_data.get("user_data", {})
        self.chat_data = serialized_data.get("chat_data", {})

        # For backwards compatibility with files not containing bot data
        self.bot_data = serialized_data.get("bot_data", self.context_types.bot_data())
        self.conversations = serialized_data.get("conversations", {})
        self.callback_data = serialized_data.get("callback_data")

        logger.debug("Persistence loaded successfully.")

    def _dump_data(self) -> bytes:
        """Dumps data into JSON format for inserting in db."""
        to_dump = {
            "chat_data": self.chat_data,
            "user_data": self.user_data,
            "bot_data": self.bot_data,
            "conversations": self.conversations,
            "callback_data": self.callback_data,
        }

        logger.debug("Dumping %s", to_dump)

        return pickle.dumps(to_dump)

    async def _update_data(self) -> None:
        logger.debug("Updating context data...")

        try:
            data = self._dump_data()
            await self._redis.set(self.__PERSISTENCE_KEY, data)
        except Exception as exc:
            logger.exception(exc)
            logger.error("Failed to update context data.")
            await self._redis.close()

        logger.debug("Context data updated successfully.")

    async def get_user_data(self) -> dict[int, UD]:
        if not self.user_data:
            await self._load_data()

        logger.debug("User data: %s", self.user_data)

        return typing.cast(dict[int, UD], deepcopy(self.user_data))

    async def get_chat_data(self) -> dict[int, CD]:
        if not self.chat_data:
            await self._load_data()

        logger.debug("Chat data: %s", self.chat_data)

        return typing.cast(dict[int, CD], deepcopy(self.chat_data))

    async def get_bot_data(self) -> BD:
        if not self.bot_data:
            await self._load_data()

        logger.debug("Bot data: %s", self.bot_data)

        return typing.cast(BD, deepcopy(self.bot_data))

    async def get_callback_data(self) -> CDCData | None:
        if not self.callback_data:
            await self._load_data()

        logger.debug("Callback data: %s", self.callback_data)

        if self.callback_data is None:
            return None

        return deepcopy(self.callback_data)  # type: ignore[arg-type]

    async def get_conversations(self, name: str) -> ConversationDict:
        if not self.conversations:
            await self._load_data()

        logger.debug("Conversations: %s", self.conversations)

        return self.conversations.get(name, {}).copy()  # type: ignore[union-attr]

    async def update_conversation(
        self,
        name: str,
        key: ConversationKey,
        new_state: object | None,
    ) -> None:
        if not self.conversations:
            self.conversations = {}

        if self.conversations.setdefault(name, {}).get(key) == new_state:
            return

        self.conversations[name][key] = new_state

        logger.debug("Conversations was updated: %s", self.conversations)

        if not self.on_flush:
            self._dump_data()

    async def update_user_data(self, user_id: int, data: UD) -> None:
        if self.user_data is None:
            self.user_data = {}

        if self.user_data.get(user_id) == data:
            return

        self.user_data[user_id] = data  # type: ignore[assignment]

        logger.debug("User data was updated: %s", self.user_data)

        if not self.on_flush:
            self._dump_data()

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        if self.chat_data is None:
            self.chat_data = {}

        if self.chat_data.get(chat_id) == data:
            return

        self.chat_data[chat_id] = data  # type: ignore[assignment]

        logger.debug("Chat data was updated: %s", self.chat_data)

        if not self.on_flush:
            self._dump_data()

    async def update_bot_data(self, data: BD) -> None:
        if self.bot_data == data:
            return

        self.bot_data = data  # type: ignore[assignment]

        logger.debug("Bot data was updated: %s", self.bot_data)

        if not self.on_flush:
            self._dump_data()

    async def update_callback_data(self, data: CDCData) -> None:
        if self.callback_data == data:
            return

        self.callback_data = data

        logger.debug("Callback data was updated: %s", self.callback_data)

        if not self.on_flush:
            self._dump_data()

    async def drop_chat_data(self, chat_id: int) -> None:
        if self.chat_data is None:
            return

        self.chat_data.pop(chat_id, None)

        logger.debug("Chat data was deleted: %s", self.chat_data)

        if not self.on_flush:
            self._dump_data()

    async def drop_user_data(self, user_id: int) -> None:
        if self.user_data is None:
            return

        self.user_data.pop(user_id, None)

        logger.debug("User data was deleted: %s", self.user_data)

        if not self.on_flush:
            self._dump_data()

    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        pass

    async def refresh_bot_data(self, bot_data: BD) -> None:
        pass

    async def flush(self) -> None:
        """
        Gives the persistence a chance to finish up saving or close a database connection gracefully.
        """

        await self._update_data()
        if not self.on_flush:
            logger.info("Closing database...")
