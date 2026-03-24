from pydantic import SecretStr
from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class LogfireSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="logfire_")

    token: SecretStr
    environment: str
    service_name: str
    send_to_logfire: bool = False
