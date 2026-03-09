from pydantic import SecretStr
from pydantic_settings import BaseSettings

from utils.config import SettingsConfig


class AgentsSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="agents_")

    mcp_proxy_url: str
    mcp_proxy_auth_token: SecretStr
    model_name: str
    model_token: SecretStr
