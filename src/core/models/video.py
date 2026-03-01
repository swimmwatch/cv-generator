import uuid
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import orm

from core import domains
from infra.db.base import Model
from infra.db.base import TimedMixin
from infra.db.utils.fields import StrEnumType


class Video(
    Model,
    TimedMixin,
):
    __tablename__ = "videos"

    MAX_SOURCE_TYPE_LENGTH = 32
    MAX_SOURCE_PK_LENGTH = 64

    MAX_PROCESSING_STATUS_LENGTH = 16

    id: orm.Mapped[UUID] = orm.mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_type: orm.Mapped[str] = orm.mapped_column(
        sa.String(MAX_SOURCE_TYPE_LENGTH),
        nullable=False,
    )
    source_pk: orm.Mapped[str] = orm.mapped_column(
        sa.String(MAX_SOURCE_PK_LENGTH),
        nullable=False,
    )

    title: orm.Mapped[str | None] = orm.mapped_column(
        sa.Text(),
        nullable=True,
    )
    description: orm.Mapped[str | None] = orm.mapped_column(
        sa.Text(),
        nullable=True,
    )

    processing_status: orm.Mapped[domains.VideoProcessingStatus] = orm.mapped_column(
        StrEnumType(
            domains.VideoProcessingStatus,
            length=MAX_PROCESSING_STATUS_LENGTH,
        ),
        nullable=False,
        default=domains.VideoProcessingStatus.PENDING,
    )

    reject_reason_codes: orm.Mapped[list[str]] = orm.mapped_column(
        sa.JSON(),
        nullable=False,
        default=list,
    )

    published_at: orm.Mapped[sa.DateTime | None] = orm.mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    duration_sec: orm.Mapped[int | None] = orm.mapped_column(
        sa.Integer(),
        nullable=True,
    )

    views: orm.Mapped[int] = orm.mapped_column(
        sa.Integer(),
        nullable=False,
        default=0,
    )
    likes: orm.Mapped[int] = orm.mapped_column(
        sa.Integer(),
        nullable=False,
        default=0,
    )
    comments: orm.Mapped[int] = orm.mapped_column(
        sa.Integer(),
        nullable=False,
        default=0,
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "source_type",
            "source_pk",
            name="uq_videos_source_type_source_pk",
        ),
        sa.Index(
            "ix_videos_source",
            "source_type",
            "source_pk",
        ),
    )
