from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class ApiSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="api_")

    title: str = "Lang Shorts API"
    description: str = ""
