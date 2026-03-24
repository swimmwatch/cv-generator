import asyncclick as click

from .createsuperuser import create_superuser
from .weaviate_migrate import weaviate_migrate


def register(group: click.Group):
    group.add_command(create_superuser)
    group.add_command(weaviate_migrate)
