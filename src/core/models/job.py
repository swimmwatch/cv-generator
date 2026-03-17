import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from infra.db.base import IdUuidMixin
from infra.db.base import Model
from infra.db.base import TimedMixin

if TYPE_CHECKING:
    from .user import User


class Job(Model, IdUuidMixin, TimedMixin):
    __tablename__ = "jobs"

    MAX_TITLE_LENGTH = 512
    MAX_URL_LENGTH = 2048

    user_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: orm.Mapped[str] = orm.mapped_column(sa.String(MAX_TITLE_LENGTH), nullable=False)
    url: orm.Mapped[str] = orm.mapped_column(sa.String(MAX_URL_LENGTH), nullable=False)
    metadata_: orm.Mapped[dict] = orm.mapped_column(
        "metadata",
        sa.JSON,
        nullable=False,
        default=dict,
    )

    user: orm.Mapped["User"] = orm.relationship(
        "User",
        back_populates="jobs",
        lazy="noload",
    )
