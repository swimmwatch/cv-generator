"""
API entrypoint.
"""

from apps.api.server import create_server_app
from apps.api.server import lifespan

app = create_server_app(lifespan)
