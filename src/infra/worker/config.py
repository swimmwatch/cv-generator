"""
Worker service configuration.
"""

from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class WorkerSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="worker_")

    broker_url: str
    result_backend: str
    concurrency: int = 1

    default_retry_count: int = 3
