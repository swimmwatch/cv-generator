"""
Database Model base class.
"""

import enum
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.hybrid import hybrid_property

convention = {
    "ix": "ix_%(column_0_label)s",  # INDEX
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",  # UNIQUE
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # CHECK
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",  # FOREIGN KEY
    "pk": "pk_%(table_name)s",  # PRIMARY KEY
}
mapper_registry = orm.registry(metadata=sa.MetaData(naming_convention=convention))


class Model(orm.DeclarativeBase):
    registry = mapper_registry
    metadata = mapper_registry.metadata


class TimedMixin:
    """
    A mixin that adds created_at, updated_at, deleted_at timestamp fields to the model.
    """

    created_at: orm.Mapped[datetime] = orm.mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: orm.Mapped[datetime] = orm.mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )
    deleted_at: orm.Mapped[datetime] = orm.mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    @hybrid_property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @is_active.inplace.expression
    @classmethod
    def _is_active_expression(cls) -> sa.ColumnElement[bool]:
        return cls.deleted_at == None  # noqa: E711


class BaseModel(Model, TimedMixin):
    """
    Base model with timestamps.
    """

    __abstract__ = True


class RelationLoadingEnum(str, enum.Enum):
    JOINED = "joined"
    SELECTIN = "selectin"
    SUBQUERY = "subquery"
