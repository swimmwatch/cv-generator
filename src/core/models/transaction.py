import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import orm

from core.domains.transaction import TransactionStatus
from infra.db.base import IdUuidMixin
from infra.db.base import Model
from infra.db.base import TimedMixin

if TYPE_CHECKING:
    from .user import User


class Transaction(Model, IdUuidMixin, TimedMixin):
    __tablename__ = "transactions"

    MAX_TELEGRAM_PAYMENT_ID_LENGTH = 256

    user_id: orm.Mapped[uuid.UUID] = orm.mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credits_amount: orm.Mapped[Decimal] = orm.mapped_column(
        sa.Numeric(precision=12, scale=2),
        nullable=False,
    )
    stars_amount: orm.Mapped[int] = orm.mapped_column(
        sa.Integer(),
        nullable=False,
    )
    status: orm.Mapped[TransactionStatus] = orm.mapped_column(
        sa.String(32),
        nullable=False,
        default=TransactionStatus.PENDING,
    )
    telegram_payment_id: orm.Mapped[str | None] = orm.mapped_column(
        sa.String(MAX_TELEGRAM_PAYMENT_ID_LENGTH),
        nullable=True,
        default=None,
    )

    user: orm.Mapped["User"] = orm.relationship(
        "User",
        back_populates="transactions",
        lazy="noload",
    )
