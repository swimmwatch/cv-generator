import enum


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
