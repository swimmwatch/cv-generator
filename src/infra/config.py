from pydantic_settings import BaseSettings

from infra.agents.config import AgentsSettings
from infra.bot.config import TelegramBotSettings
from infra.db.config import DatabaseSettings
from infra.logfire.config import LogfireSettings
from infra.logger.config import LoggerSettings
from infra.redis.config import RedisSettings
from infra.s3.config import S3Settings
from infra.weaviate.config import WeaviateSettings
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
    weaviate: WeaviateSettings = WeaviateSettings()
    logger: LoggerSettings = LoggerSettings()
    telegram_bot: TelegramBotSettings = TelegramBotSettings()
    worker: WorkerSettings = WorkerSettings()
    agents: AgentsSettings = AgentsSettings()
    logfire: LogfireSettings = LogfireSettings()
