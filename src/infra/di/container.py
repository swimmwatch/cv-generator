"""
DI container.
"""

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
from infra.mongo.client import AsyncMongoDatabase
from infra.mongo.transactions import AsyncMongoTransactionManager
from infra.youtube.client import YouTubeDataApiV3Client
from utils.transactions.manager import AsyncTransactionManager
from utils.yt.dlp import YtDlpVideoMetadataClient

logger = get_logger(__name__)


class Container(DeclarativeContainer):
    config = providers.Configuration(pydantic_settings=[Settings()])

    telegram_template = providers.Singleton(
        TelegramTemplate,
        template_dir=config.telegram_bot.template_dir,
        babel_domain=config.telegram_bot.babel_domain,
        babel_locale_dir=config.telegram_bot.babel_locale_dir,
    )

    # MongoDB
    async_mongo_db = providers.Singleton(
        AsyncMongoDatabase,
        url=config.mongo.url,
        db_name=config.mongo.db,
    )
    async_mongo_transaction_manager = providers.Factory(
        AsyncMongoTransactionManager,
        client=providers.Factory(
            lambda db: db.client,
            async_mongo_db,
        ),
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
            async_mongo_transaction_manager,
        ),
    )

    # DALs
    user_async_dal = providers.Factory(
        dal.UserAsyncDAL,
        session=scoped_async_session,
    )
    video_async_dal = providers.Factory(
        dal.VideoAsyncDAL,
        session=scoped_async_session,
    )

    # Repositories
    sql_user_repo = providers.Factory(
        repos.SqlAlchemyUserRepository,
        session=scoped_async_session,
    )
    sql_video_repo = providers.Factory(
        repos.SqlAlchemyVideoRepository,
        session=scoped_async_session,
    )
    mongo_video_metadata_repo = providers.Factory(
        repos.MongoVideoMetadataRepository,
        collection=providers.Factory(
            lambda db: db.db["video_metadata"],
            async_mongo_db,
        ),
    )

    # External clients
    youtube_client = providers.Factory(
        YouTubeDataApiV3Client,
        api_key=config.youtube.data_api_key,
    )
    yt_dlp_metadata_client = providers.Factory(
        YtDlpVideoMetadataClient,
    )

    # Services
    user_service = providers.Factory(
        services.UserService,
        user_repo=sql_user_repo,
    )
