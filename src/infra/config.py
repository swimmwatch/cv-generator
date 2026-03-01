from pydantic_settings import BaseSettings

from infra.admin.config import AdminSettings
from infra.api.config import ApiSettings
from infra.bot.config import TelegramBotSettings
from infra.db.config import DatabaseSettings
from infra.logger.config import LoggerSettings
from infra.mongo.config import MongoSettings
from infra.redis.config import RedisSettings
from infra.worker.config import WorkerSettings
from infra.youtube.config import YouTubeSettings
from utils.config import RunLevelBaseConfigMixin
from utils.config import SettingsConfig


class Settings(
    RunLevelBaseConfigMixin,
    BaseSettings,
):
    model_config = SettingsConfig()

    debug: bool = True
    tag: str = "untagged"

    db: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    mongo: MongoSettings = MongoSettings()
    logger: LoggerSettings = LoggerSettings()
    api: ApiSettings = ApiSettings()
    telegram_bot: TelegramBotSettings = TelegramBotSettings()
    admin: AdminSettings = AdminSettings()
    worker: WorkerSettings = WorkerSettings()
    youtube: YouTubeSettings = YouTubeSettings()
