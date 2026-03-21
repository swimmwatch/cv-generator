"""
DI container.
"""

from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer
from redis.asyncio import Redis as AsyncRedis

from core import dal
from core import repos
from core import services
from infra.agents.chat import ChatAgent
from infra.agents.cv_generator import CvGeneratorAgent
from infra.agents.job_parser import JobParserAgent
from infra.agents.renderer import ResumeRenderer
from infra.bot.template import TelegramTemplate
from infra.config import Settings
from infra.db.client import AsyncDatabase
from infra.db.utils.transactions import AsyncSqlAlchemyTransactionManager
from infra.di.resources import init_agent_checkpointer
from infra.di.resources import init_tg_bot
from infra.redis.transactions import AsyncRedisTransactionManager
from infra.weaviate.client import WeaviateClient
from utils.storages.impl.s3 import S3AsyncStorage
from utils.transactions.manager import AsyncTransactionManager


class Container(DeclarativeContainer):
    config = providers.Configuration(pydantic_settings=[Settings()])

    telegram_template = providers.Singleton(
        TelegramTemplate,
        template_dir=config.telegram_bot.template_dir,
        babel_domain=config.telegram_bot.babel_domain,
        babel_locale_dir=config.telegram_bot.babel_locale_dir,
    )
    resume_renderer = providers.Singleton(
        ResumeRenderer,
        babel_domain=config.telegram_bot.babel_domain,
        babel_locale_dir=config.telegram_bot.babel_locale_dir,
    )

    # Redis
    redis_client = providers.Singleton(
        AsyncRedis,
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
    )
    redis_async_transaction_manager = providers.Factory(
        AsyncRedisTransactionManager,
        redis_client=redis_client,
    )
    redis_job_state_repo = providers.Factory(
        repos.RedisJobStateRepository,
        redis_client=redis_client,
    )
    redis_chat_state_repo = providers.Factory(
        repos.RedisChatStateRepository,
        redis_client=redis_client,
    )
    redis_resume_state_repo = providers.Factory(
        repos.RedisResumeStateRepository,
        redis_client=redis_client,
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
    resume_async_dal = providers.Factory(
        dal.ResumeAsyncDAL,
        session=scoped_async_session,
    )

    # Repositories
    sql_user_repo = providers.Factory(
        repos.SqlAlchemyUserRepository,
        session=scoped_async_session,
    )
    sql_resume_repo = providers.Factory(
        repos.SqlAlchemyResumeRepository,
        session=scoped_async_session,
    )
    sql_job_repo = providers.Factory(
        repos.SqlAlchemyJobRepository,
        session=scoped_async_session,
    )
    sql_generated_cv_repo = providers.Factory(
        repos.SqlAlchemyGeneratedCVRepository,
        session=scoped_async_session,
    )
    sql_transaction_repo = providers.Factory(
        repos.SqlAlchemyTransactionRepository,
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

    # Weaviate
    weaviate_client = providers.Singleton(
        WeaviateClient,
        http_host=config.weaviate.http_host,
        http_port=config.weaviate.http_port,
        grpc_host=config.weaviate.grpc_host,
        grpc_port=config.weaviate.grpc_port,
    )
    weaviate_async_client = providers.Factory(
        lambda wc: wc.client,
        weaviate_client,
    )

    # DALs (Weaviate)
    resume_metadata_dal = providers.Factory(
        dal.ResumeMetadataDAL,
        client=weaviate_async_client,
    )
    job_metadata_dal = providers.Factory(
        dal.JobMetadataDAL,
        client=weaviate_async_client,
    )

    # Repositories (Weaviate)
    weaviate_resume_metadata_repo = providers.Factory(
        repos.WeaviateResumeMetadataRepository,
        resume_metadata_dal=resume_metadata_dal,
    )
    weaviate_job_metadata_repo = providers.Factory(
        repos.WeaviateJobMetadataRepository,
        job_metadata_dal=job_metadata_dal,
    )

    # Services
    user_service = providers.Factory(
        services.UserService,
        user_repo=sql_user_repo,
    )
    resume_service = providers.Factory(
        services.ResumeService,
        async_storage=s3_async_storage,
        resume_metadata_repo=weaviate_resume_metadata_repo,
        resume_repo=sql_resume_repo,
    )
    job_service = providers.Factory(
        services.JobService,
        job_metadata_repo=weaviate_job_metadata_repo,
        job_repo=sql_job_repo,
    )
    generated_cv_service = providers.Factory(
        services.GeneratedCVService,
        async_storage=s3_async_storage,
        generated_cv_repo=sql_generated_cv_repo,
    )
    transaction_service = providers.Factory(
        services.TransactionService,
        transaction_repo=sql_transaction_repo,
        user_repo=sql_user_repo,
    )

    # Agents
    agent_checkpointer = providers.Resource(
        init_agent_checkpointer,
        redis_url=config.redis.checkpoint_url,
        ttl=providers.Dict(default_ttl=providers.Object(60)),
    )
    mcp_proxy_headers = providers.Dict(
        Authorization=providers.Callable(
            lambda secret: f"Bearer {secret.get_secret_value()}",
            config.agents.mcp_proxy_auth_token,
        ),
    )
    job_parser_agent = providers.Factory(
        JobParserAgent,
        model_name=config.agents.model_name,
        model_token=providers.Callable(
            lambda secret: secret.get_secret_value(),
            config.agents.model_token,
        ),
        mcp_proxy_url=config.agents.mcp_proxy_url,
        mcp_headers=mcp_proxy_headers,
        checkpointer=agent_checkpointer,
    )
    cv_generator_agent = providers.Factory(
        CvGeneratorAgent,
        model_name=config.agents.model_name,
        model_token=providers.Callable(
            lambda secret: secret.get_secret_value(),
            config.agents.model_token,
        ),
        resume_metadata_repo=weaviate_resume_metadata_repo,
        job_metadata_repo=weaviate_job_metadata_repo,
        checkpointer=agent_checkpointer,
    )
    chat_agent = providers.Factory(
        ChatAgent,
        model_name=config.agents.model_name,
        model_token=providers.Callable(
            lambda secret: secret.get_secret_value(),
            config.agents.model_token,
        ),
        resume_metadata_repo=weaviate_resume_metadata_repo,
        job_metadata_repo=weaviate_job_metadata_repo,
    )

    # External services
    tg_bot_client = providers.Resource(
        init_tg_bot,
        token=providers.Callable(
            lambda secret: secret.get_secret_value(),
            config.telegram_bot.token,
        ),
    )
