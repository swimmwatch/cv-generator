import os
import typing
from pathlib import Path
from typing import AsyncGenerator

import fakeredis
import pytest
import pytest_asyncio
import sqlalchemy as sa
import structlog
from alembic.command import upgrade
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy_utils import create_database
from sqlalchemy_utils import database_exists
from sqlalchemy_utils import drop_database
from structlog.testing import LogCapture

from infra.db.config import DatabaseSettings
from infra.logger.utils import get_logger
from tests.factories.base import BaseSQLAFactory
from utils.tests.utils import DontCloseAsyncSessionCM

logger = get_logger(__name__)

pytest_plugins = (
    "tests.dal",
    "tests.repos",
    "tests.services",
    "tests.factories.user",
    "tests.factories.resume",
    "tests.factories.job",
    "tests.factories.generated_cv",
)


@pytest.fixture(name="log_output")
def fixture_log_output() -> LogCapture:
    return LogCapture()


@pytest.fixture(autouse=True)
def _fixture_configure_structlog(log_output: LogCapture) -> None:
    structlog.configure(processors=[log_output])


def _upgrade_head(url: str, rootdir: str) -> None:
    """
    Upgrade the test database to head.

    :param url: Database URL
    :param rootdir: Root project directory
    """
    config = Config()
    alembic_folder = Path(rootdir) / "src" / "infra" / "db" / "migrations"
    config.set_main_option("script_location", str(alembic_folder))
    config.set_main_option("utils.url", url)

    # heads means all migrations from all branches (in case there are split branches)
    upgrade(config, "heads")


@pytest.fixture(scope="session")
def db_engine(request, worker_id: str) -> typing.Generator[sa.Engine, None, None]:
    os.environ["DB_NAME"] = f"test_{worker_id or 'master'}"  # override default database
    settings = DatabaseSettings()

    if not database_exists(settings.url):
        logger.info("Database does not exist. Creating new database for tests: %s", settings.name)
        create_database(settings.url)
    else:
        logger.info("Database already exists. Using existing database for tests: %s", settings.name)

    engine = sa.create_engine(settings.url)

    _upgrade_head(settings.url, request.config.rootdir)

    try:
        yield engine
    finally:
        engine.dispose()
        drop_database(settings.url)
        logger.info(f"Database dropped: {settings.name}")


@pytest.fixture(scope="session")
async def async_db_engine(request, worker_id: str) -> AsyncGenerator[AsyncEngine, None]:
    os.environ["DB_NAME"] = f"test_async_{worker_id or 'master'}"
    settings = DatabaseSettings()

    if not database_exists(settings.url):
        logger.info("Database does not exist. Creating new database for tests: %s", settings.name)
        create_database(settings.url)
    else:
        logger.info("Database already exists. Using existing database for tests: %s", settings.name)

    engine = create_async_engine(
        settings.url,
        future=True,
        echo=False,
        pool_pre_ping=True,
    )

    _upgrade_head(settings.url, request.config.rootdir)

    try:
        yield engine
    finally:
        await engine.dispose()
        drop_database(settings.url)
        logger.info(f"Database dropped: {settings.name}")


@pytest.fixture
def alembic_engine(db_engine: sa.Engine) -> sa.Engine:
    """
    Override "alembic_engine" fixture of "pytest-alembic" package.

    Check: https://pytest-alembic.readthedocs.io/en/latest/api.html#pytest_alembic.plugin.fixtures.alembic_engine

    :param db_engine: SQLAlchemy Engine instance
    :return: SQLAlchemy Engine instance
    """
    return db_engine


@pytest.fixture
async def async_db_session(async_db_engine: AsyncEngine):
    connection = await async_db_engine.connect()
    transaction = await connection.begin_nested()
    session_maker = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        class_=AsyncSession,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    session = session_maker()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture
def redis_client() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


@pytest.fixture
def async_redis_client() -> fakeredis.FakeAsyncRedis:
    return fakeredis.FakeAsyncRedis()


@pytest_asyncio.fixture(autouse=True)
async def _wire_polyfactory_to_test_session(async_db_session: AsyncSession):
    BaseSQLAFactory.__async_session__ = lambda: DontCloseAsyncSessionCM(async_db_session)  # type: ignore[assignment]
    yield
    BaseSQLAFactory.__async_session__ = None
