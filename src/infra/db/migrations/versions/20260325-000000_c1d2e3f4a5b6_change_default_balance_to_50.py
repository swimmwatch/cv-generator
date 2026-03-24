"""change_default_balance_to_50

Revision ID: c1d2e3f4a5b6
Revises: df5654cecf62
Create Date: 2026-03-25 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "df5654cecf62"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "balance",
        existing_type=sa.Numeric(precision=12, scale=2),
        server_default="50",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "balance",
        existing_type=sa.Numeric(precision=12, scale=2),
        server_default="10",
        existing_nullable=False,
    )
