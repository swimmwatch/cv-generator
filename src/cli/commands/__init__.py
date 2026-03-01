import asyncclick as click

from .createsuperuser import create_superuser


def register(group: click.Group):
    group.add_command(create_superuser)
