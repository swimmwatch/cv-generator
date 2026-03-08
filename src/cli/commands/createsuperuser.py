import asyncclick as click
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import dto
from core import repos
from core import services
from infra.db.client import AsyncDatabase


@click.command("createsuperuser")
@inject
async def create_superuser(
    db: "AsyncDatabase" = Provide["async_db"],
    user_service: "services.UserService" = Provide["user_service"],
    user_repo: "repos.UserRepository" = Provide["sql_user_repo"],
):
    click.echo("Creating superuser...")
    username = await click.prompt("Username")
    username = username.strip()

    if await user_repo.get_by_username(username):
        click.echo("User with this username already exists!", err=True, color=True)
        return

    first_name = await click.prompt("First name")
    first_name = first_name.strip()
    last_name = await click.prompt("Last name", default=None)
    last_name = last_name.strip() if last_name else None

    password = await click.prompt("Password", hide_input=True)
    password = password.strip()

    messenger_id = await click.prompt("Messenger ID")
    messenger_id = messenger_id.strip()

    data = dto.UserAdminCreateDTO(
        messenger_id=messenger_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        password=password,
    )
    await user_service.create_superuser(data)

    await db.commit_scoped_session()

    click.echo("Superuser was created successfully!")
