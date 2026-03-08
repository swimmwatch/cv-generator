import pydantic
from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class S3Settings(BaseSettings):
    model_config = SettingsConfig(env_prefix="s3_")

    url: str
    bucket: str
    access_key: pydantic.SecretStr
    secret_key: pydantic.SecretStr
