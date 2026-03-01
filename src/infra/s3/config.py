import pydantic
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from utils.config import RunLevelBaseConfigMixin


class S3Settings(RunLevelBaseConfigMixin, BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="minio_",
        env_file=(".env", ".env.local"),
        extra="allow",
    )

    url: str
    root_user: str
    root_password: pydantic.SecretStr
    access_key: pydantic.SecretStr
    secret_key: pydantic.SecretStr
