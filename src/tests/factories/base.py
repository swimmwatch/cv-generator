import typing

from polyfactory.factories.sqlalchemy_factory import SQLAlchemyFactory

T = typing.TypeVar("T")


class BaseSQLAFactory(SQLAlchemyFactory[T]):
    __is_base_factory__ = True
