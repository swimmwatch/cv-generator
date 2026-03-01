from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class LoggerSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="logger_")

    level: str = "DEBUG"
    json_output: bool = False
