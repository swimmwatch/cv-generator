"""
Database service configuration.
"""

from pydantic import computed_field
from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="db_")

    host: str
    port: int = 5432
    user: str
    password: str
    name: str
    debug: bool = True
    driver: str = "postgresql+psycopg"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        return f"{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
