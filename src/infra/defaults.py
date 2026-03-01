from pathlib import Path

import pytz

BASE_DIR = Path(__file__).resolve().parent.parent
BASE_APPS_DIR = BASE_DIR / "apps"
BASE_INFRA_DIR = BASE_DIR / "infra"
BASE_INFRA_BOT_DIR = BASE_INFRA_DIR / "bot"

SUPPORTED_LOCALES = [
    "en",
    "ru",
]

DEFAULT_TIMEZONE_NAME = "UTC"  # Default timezone for the application
DEFAULT_TIMEZONE = pytz.timezone(DEFAULT_TIMEZONE_NAME)
