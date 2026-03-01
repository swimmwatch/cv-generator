from pydantic import computed_field
from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class MongoSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="mongo_")

    host: str = "localhost"
    port: int = 27017
    db: str = "lang_shorts"
    user: str = ""
    password: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def url(self) -> str:
        if self.user and self.password:
            return f"mongodb://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}?authSource=admin"
        return f"mongodb://{self.host}:{self.port}/{self.db}"
