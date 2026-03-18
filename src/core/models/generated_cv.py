import uuid
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from infra.db.base import IdUuidMixin
from infra.db.base import Model
from infra.db.base import TimedMixin

if TYPE_CHECKING:
    from .job import Job
    from .resume import Resume
    from .user import User


class GeneratedCV(Model, IdUuidMixin, TimedMixin):
    __tablename__ = "generated_cvs"

    MAX_OBJECT_NAME_LENGTH = 512
    MAX_FILE_NAME_LENGTH = 256

    user_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    object_name: orm.Mapped[str] = orm.mapped_column(sa.String(MAX_OBJECT_NAME_LENGTH), nullable=False)
    file_name: orm.Mapped[str] = orm.mapped_column(sa.String(MAX_FILE_NAME_LENGTH), nullable=False)

    user: orm.Mapped["User"] = orm.relationship(
        "User",
        back_populates="generated_cvs",
        lazy="noload",
    )
    resume: orm.Mapped["Resume"] = orm.relationship(
        "Resume",
        back_populates="generated_cvs",
        lazy="noload",
    )
    job: orm.Mapped["Job"] = orm.relationship(
        "Job",
        back_populates="generated_cvs",
        lazy="noload",
    )
