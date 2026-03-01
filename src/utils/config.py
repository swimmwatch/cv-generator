"""
Common configuration.
"""

from enum import StrEnum
from functools import partial

from pydantic import Field
from pydantic_settings import SettingsConfigDict


class RunLevelEnum(StrEnum):
    PRODUCTION = "prod"
    DEVELOPMENT = "dev"
    LOCAL = "local"


class RunLevelBaseConfigMixin:
    env: RunLevelEnum = Field(..., alias="ENV")


SettingsConfig = partial(
    SettingsConfigDict,
    env_file=(".env", ".env.local", "../.env.local"),
    extra="allow",
)
