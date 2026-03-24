"""remove_job_resume_id

Revision ID: eb3e64151167
Revises: 85fcebbdde1a
Create Date: 2026-03-17 19:53:06.392999

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "eb3e64151167"
down_revision = "85fcebbdde1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("fk_jobs_resume_id_resumes"), "jobs", type_="foreignkey")
    op.drop_index(op.f("ix_jobs_resume_id"), table_name="jobs")
    op.drop_column("jobs", "resume_id")


def downgrade() -> None:
    op.add_column("jobs", sa.Column("resume_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_jobs_resume_id"), "jobs", ["resume_id"])
    op.create_foreign_key(
        op.f("fk_jobs_resume_id_resumes"), "jobs", "resumes", ["resume_id"], ["id"], ondelete="CASCADE"
    )
