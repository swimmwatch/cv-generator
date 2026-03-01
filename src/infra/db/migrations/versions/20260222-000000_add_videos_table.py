"""Add videos table

Revision ID: add_videos_table
Revises: 5394928c7170
Create Date: 2026-02-22

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_videos_table"
down_revision = "5394928c7170"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_pk", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("processing_status", sa.String(length=16), nullable=False),
        sa.Column("reject_reason_codes", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_sec", sa.Integer(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("likes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("comments", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_videos")),
        sa.UniqueConstraint("source_type", "source_pk", name=op.f("uq_videos_source_type_source_pk")),
    )

    op.create_index(op.f("ix_videos_source"), "videos", ["source_type", "source_pk"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_videos_source"), table_name="videos")
    op.drop_table("videos")
