import pydantic
from pydantic_settings import BaseSettings

from utils.config import RunLevelBaseConfigMixin
from utils.config import SettingsConfig


class AdminSettings(RunLevelBaseConfigMixin, BaseSettings):
    model_config = SettingsConfig(env_prefix="admin_")

    session_secret: pydantic.SecretStr
