import enum
import typing

import sqlalchemy as sa

EnumT = typing.TypeVar("EnumT", bound=enum.StrEnum)


class StrEnumType(sa.TypeDecorator[EnumT]):
    """Store a StrEnum as a plain string in the DB.

    - DB type is VARCHAR.
    - Python type is the given enum class.

    Alembic integration:

    - `load_dialect_impl` ensures the reflected type is a plain String.
    - `compare_against_backend` tells autogenerate there's no DDL diff as long as the
      backend type is a String with compatible length.
    """

    impl = sa.String
    cache_ok = True

    def __init__(self, enum_cls: type[EnumT], *, length: int = 32) -> None:
        super().__init__(length=length)
        self._enum_cls = enum_cls
        self._length = length

    def load_dialect_impl(self, dialect: sa.Dialect) -> sa.types.TypeEngine:
        return dialect.type_descriptor(sa.String(length=self._length))

    def compare_against_backend(
        self,
        dialect: sa.Dialect,
        conn_type: sa.types.TypeEngine,
    ) -> bool:
        # Return False => "no change".
        if isinstance(conn_type, sa.String):
            # Be lenient: treat missing/None length as compatible.
            if conn_type.length is None or conn_type.length >= self._length:
                return False
        return False

    def process_bind_param(self, value: EnumT | str | None, dialect: sa.Dialect) -> str | None:
        if value is None:
            return None

        if isinstance(value, self._enum_cls):
            return value.value

        if isinstance(value, str):
            # Allow already-serialized values.
            return value

        raise TypeError(f"Expected {self._enum_cls.__name__} or str, got {type(value)!r}")

    def process_result_value(self, value: str | None, dialect: sa.Dialect) -> EnumT | None:
        if value is None:
            return None
        return self._enum_cls(value)

    @property
    def python_type(self) -> type[EnumT]:  # type: ignore[override]
        return self._enum_cls

    def __repr__(self) -> str:  # pragma: no cover
        return f"String(length={self._length})"

    def __str__(self) -> str:  # pragma: no cover
        return self.__repr__()
