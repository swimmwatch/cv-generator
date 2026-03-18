from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.hybrid import hybrid_property

from infra.db.base import IdUuidMixin
from infra.db.base import Model
from infra.db.base import TimedMixin

if TYPE_CHECKING:
    from .generated_cv import GeneratedCV
    from .job import Job
    from .resume import Resume


class User(
    Model,
    IdUuidMixin,
    TimedMixin,
):
    __tablename__ = "users"

    MAX_MESSENGER_ID_LENGTH = 256
    MAX_USERNAME_LENGTH = 64
    MAX_FIRST_NAME_LENGTH = 128
    MAX_LAST_NAME_LENGTH = 128
    MAX_PASSWORD_HASH_LENGTH = 256
    MAX_LANGUAGE_CODE_LENGTH = 16

    messenger_id: orm.Mapped[str] = orm.mapped_column(
        sa.String(MAX_MESSENGER_ID_LENGTH),
        unique=True,
        nullable=False,
        index=True,
    )

    username: orm.Mapped[str | None] = orm.mapped_column(
        sa.String(MAX_USERNAME_LENGTH),
        nullable=True,
    )
    first_name: orm.Mapped[str] = orm.mapped_column(
        sa.String(MAX_FIRST_NAME_LENGTH),
        nullable=False,
    )
    last_name: orm.Mapped[str | None] = orm.mapped_column(
        sa.String(MAX_LAST_NAME_LENGTH),
        nullable=True,
        default=None,
    )
    password_hash: orm.Mapped[str | None] = orm.mapped_column(
        sa.String(MAX_PASSWORD_HASH_LENGTH),
        nullable=True,
        default=None,
    )

    # Admin fields
    is_staff: orm.Mapped[bool] = orm.mapped_column(
        sa.Boolean(),
        nullable=False,
        default=False,
    )
    is_superuser: orm.Mapped[bool] = orm.mapped_column(
        sa.Boolean(),
        nullable=False,
        default=False,
    )

    language_code: orm.Mapped[str | None] = orm.mapped_column(
        sa.String(MAX_LANGUAGE_CODE_LENGTH),
        nullable=True,
    )

    resumes: orm.Mapped[list["Resume"]] = orm.relationship(
        "Resume",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    jobs: orm.Mapped[list["Job"]] = orm.relationship(
        "Job",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    generated_cvs: orm.Mapped[list["GeneratedCV"]] = orm.relationship(
        "GeneratedCV",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    @hybrid_property
    def full_name(self) -> str:
        full_name = self.first_name

        if self.last_name:
            full_name += " " + self.last_name

        return full_name

    @full_name.inplace.expression
    @classmethod
    def _full_name_expression(cls) -> sa.ColumnElement[str]:
        return sa.case(
            (cls.last_name != None, cls.first_name + " " + cls.last_name),  # noqa: E711
            else_=cls.first_name,
        )
