from pathlib import Path

from pydantic import SecretStr
from pydantic import computed_field
from pydantic_settings import BaseSettings
from telegram_webapp_auth.auth import generate_secret_key

from infra.defaults import BASE_DIR
from infra.defaults import BASE_INFRA_BOT_DIR
from utils.config import SettingsConfig


class TelegramBotSettings(BaseSettings):
    model_config = SettingsConfig(env_prefix="telegram_bot_")

    title: str = "CV Generator Bot API"
    description: str = ""

    token: SecretStr
    template_dir: Path = BASE_INFRA_BOT_DIR / "templates"
    babel_domain: str = "messages"
    babel_locale_dir: Path = BASE_DIR / "locale"
    persistence_db: int = 3

    # Polling settings
    timeout: int = 30
    read_timeout: int = 30
    write_timeout: int = 30
    connect_timeout: int = 30
    pool_timeout: int = 30

    # Webhook settings
    webhook_url: str
    webhook_secret_token: SecretStr

    @computed_field  # type: ignore[prop-decorator]
    @property
    def secret_key(self) -> bytes:
        return generate_secret_key(self.token.get_secret_value())
