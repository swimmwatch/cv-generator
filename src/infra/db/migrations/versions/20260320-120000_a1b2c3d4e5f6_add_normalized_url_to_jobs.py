"""add_normalized_url_to_jobs

Revision ID: a1b2c3d4e5f6
Revises: b97b3c11fa81
Create Date: 2026-03-20 12:00:00.000000

"""

from urllib.parse import urlparse

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "b97b3c11fa81"
branch_labels = None
depends_on = None


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = parsed.path.rstrip("/")
    return f"{host}{path}"


def upgrade() -> None:
    op.add_column("jobs", sa.Column("normalized_url", sa.String(length=2048), nullable=True))

    conn = op.get_bind()
    jobs = conn.execute(sa.text("SELECT id, url FROM jobs")).fetchall()
    for job_id, url in jobs:
        normalized = _normalize_url(url)
        conn.execute(
            sa.text("UPDATE jobs SET normalized_url = :normalized WHERE id = :id"),
            {"normalized": normalized, "id": job_id},
        )

    op.alter_column("jobs", "normalized_url", nullable=False)
    op.create_index(op.f("ix_jobs_normalized_url"), "jobs", ["normalized_url"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_normalized_url"), table_name="jobs")
    op.drop_column("jobs", "normalized_url")
