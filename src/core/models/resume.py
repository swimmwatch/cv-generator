import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from core import domains
from infra.db.base import IdUuidMixin
from infra.db.base import Model
from infra.db.base import TimedMixin
from infra.db.utils.fields import StrEnumType

if TYPE_CHECKING:
    from .user import User


class Resume(Model, IdUuidMixin, TimedMixin):
    __tablename__ = "resumes"

    MAX_TITLE_LENGTH = 256
    MAX_OBJECT_NAME_LENGTH = 512
    MAX_FILE_NAME_LENGTH = 256

    user_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: orm.Mapped[str | None] = orm.mapped_column(sa.String(MAX_TITLE_LENGTH), nullable=True)
    object_name: orm.Mapped[str] = orm.mapped_column(sa.String(MAX_OBJECT_NAME_LENGTH), nullable=False)
    file_name: orm.Mapped[str] = orm.mapped_column(sa.String(MAX_FILE_NAME_LENGTH), nullable=False)
    status: orm.Mapped[domains.ResumeProcessingStatus] = orm.mapped_column(
        StrEnumType(domains.ResumeProcessingStatus),
        nullable=False,
        default=domains.ResumeProcessingStatus.PENDING,
    )

    user: orm.Mapped["User"] = orm.relationship(
        "User",
        back_populates="resumes",
        lazy="noload",
    )
