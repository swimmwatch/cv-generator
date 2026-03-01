from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class YouTubeSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="youtube_")

    enabled: bool = False
    region_code: str = "US"
    time_window_days: int = 7
    seed_strategy: str = "mostPopular"

    data_api_key: str | None = None
