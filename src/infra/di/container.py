"""
DI container.
"""

from aiogram import Bot
from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer

from core import dal
from core import repos
from core import services
from infra.bot.template import TelegramTemplate
from infra.config import Settings
from infra.db.client import AsyncDatabase
from infra.db.utils.transactions import AsyncSqlAlchemyTransactionManager
from infra.logger.utils import get_logger
from utils.storages.impl.s3 import S3AsyncStorage
from utils.transactions.manager import AsyncTransactionManager

logger = get_logger(__name__)


class Container(DeclarativeContainer):
    config = providers.Configuration(pydantic_settings=[Settings()])

    telegram_template = providers.Singleton(
        TelegramTemplate,
        template_dir=config.telegram_bot.template_dir,
        babel_domain=config.telegram_bot.babel_domain,
        babel_locale_dir=config.telegram_bot.babel_locale_dir,
    )

    # Database
    async_db = providers.Singleton(
        AsyncDatabase,
        db_url=config.db.url,
    )
    scoped_async_session = providers.Factory(
        lambda db: db.get_scoped_session(),
        async_db,
    )
    async_sql_transaction_manager_scoped = providers.Factory(
        AsyncSqlAlchemyTransactionManager,
        session=scoped_async_session,
    )

    # Transaction manager
    async_transaction_manager_scoped = providers.Factory(
        AsyncTransactionManager,
        managers=providers.List(
            async_sql_transaction_manager_scoped,
        ),
    )

    # DALs
    user_async_dal = providers.Factory(
        dal.UserAsyncDAL,
        session=scoped_async_session,
    )

    # Repositories
    sql_user_repo = providers.Factory(
        repos.SqlAlchemyUserRepository,
        session=scoped_async_session,
    )

    # S3
    s3_async_storage = providers.Factory(
        S3AsyncStorage,
        bucket=config.s3.bucket,
        endpoint_url=config.s3.url,
        aws_access_key_id=providers.Callable(
            lambda secret: secret.get_secret_value(),
            config.s3.access_key,
        ),
        aws_secret_access_key=providers.Callable(
            lambda secret: secret.get_secret_value(),
            config.s3.secret_key,
        ),
    )

    # Services
    user_service = providers.Factory(
        services.UserService,
        user_repo=sql_user_repo,
    )

    resume_service = providers.Factory(
        services.ResumeService,
        async_storage=s3_async_storage,
    )

    # External services
    tg_bot_client = providers.Factory(
        Bot,
        token=providers.Callable(
            lambda secret: secret.get_secret_value(),
            config.telegram_bot.token,
        ),
    )
