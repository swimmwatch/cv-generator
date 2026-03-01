"""
Sync database client.
"""

from contextlib import contextmanager

import sqlalchemy as sa
import sqlalchemy.orm as orm

from infra.db.utils.types import SessionGenerator
from infra.logger.utils import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(self, db_url: str, echo: bool = False) -> None:
        self._engine = sa.create_engine(db_url, echo=echo)
        logger.debug("Database engine was created")

        self._session_factory = orm.scoped_session(
            orm.sessionmaker(
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
                bind=self._engine,
            ),
        )

    @contextmanager
    def session(self) -> SessionGenerator:
        session: orm.Session = self._session_factory()
        logger.debug("Database session was created")

        try:
            yield session
        except Exception:
            session.rollback()
            logger.debug("Database session was rolled back")
            raise
        finally:
            session.close()
            logger.debug("Database session was closed")

    def stop(self) -> None:
        self._engine.dispose()
        logger.debug("Database engine was disposed")
