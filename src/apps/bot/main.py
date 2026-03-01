"""
Telegram Bot entrypoint.
"""

from apps.bot.server import create_server_app
from apps.bot.server import lifespan

app = create_server_app(lifespan)
