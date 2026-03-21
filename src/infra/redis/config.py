"""
Redis configuration.
"""

from pydantic import computed_field
from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class RedisSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="redis_")

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    checkpoint_url: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"
