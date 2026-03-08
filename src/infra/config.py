from pydantic_settings import BaseSettings

from infra.admin.config import AdminSettings
from infra.api.config import ApiSettings
from infra.bot.config import TelegramBotSettings
from infra.db.config import DatabaseSettings
from infra.logger.config import LoggerSettings
from infra.redis.config import RedisSettings
from infra.s3.config import S3Settings
from infra.worker.config import WorkerSettings
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
    s3: S3Settings = S3Settings()
    logger: LoggerSettings = LoggerSettings()
    api: ApiSettings = ApiSettings()
    telegram_bot: TelegramBotSettings = TelegramBotSettings()
    admin: AdminSettings = AdminSettings()
    worker: WorkerSettings = WorkerSettings()
