import abc
import typing

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.orm.strategy_options import _AbstractLoad
from sqlalchemy.sql import operators

from infra.db.base import Model
from infra.db.base import RelationLoadingEnum
from utils.dal import BaseAsyncDAL


class BaseLookup:
    class Meta:
        label: str = ""

    def __call__(self, *args, **kwargs):
        return self


class IsNullLookup(BaseLookup):
    class Meta:
        label = "isnull"

    def __call__(self, column: sa.Column[typing.Any], value: bool) -> sa.ColumnElement[bool]:
        return (column == None) if value else (column != None)  # noqa: E711


class IsExactLookup(BaseLookup):
    class Meta:
        label = "exact"

    def __call__(self, column: sa.Column[typing.Any], value: typing.Any) -> sa.ColumnElement[bool]:
        return column == value


class BaseSqlAlchemyDAL(abc.ABC):
    _LOADING_FUNCS: dict[RelationLoadingEnum, typing.Callable[..., _AbstractLoad]] = {
        RelationLoadingEnum.JOINED: orm.joinedload,
        RelationLoadingEnum.SELECTIN: orm.selectinload,
        RelationLoadingEnum.SUBQUERY: orm.subqueryload,
    }
    _LOADING_SEP = "__"
    _RELATION_LOAD_FIELD = "load"

    _UNDERSCORE_OPERATORS: dict[str, typing.Callable] = {
        "isnull": lambda c, v: (c == None) if v else (c != None),  # noqa: E711
        "exact": operators.eq,
        "ne": operators.ne,  # not equal or is not (for None)
        "gt": operators.gt,
        "ge": operators.ge,
        "lt": operators.lt,
        "le": operators.le,
        "in": operators.in_op,
        "notin": operators.notin_op,
        "between": lambda c, v: c.between(v[0], v[1]),
        "like": operators.like_op,
        "ilike": operators.ilike_op,
        "startswith": operators.startswith_op,
        "istartswith": lambda c, v: c.ilike(v + "%"),
        "endswith": operators.endswith_op,
        "iendswith": lambda c, v: c.ilike("%" + v),
        "contains": lambda c, v: c.ilike(f"%{v}%"),
        "year": lambda c, v: sa.extract("year", c) == v,
        "year_ne": lambda c, v: sa.extract("year", c) != v,
        "year_gt": lambda c, v: sa.extract("year", c) > v,
        "year_ge": lambda c, v: sa.extract("year", c) >= v,
        "year_lt": lambda c, v: sa.extract("year", c) < v,
        "year_le": lambda c, v: sa.extract("year", c) <= v,
        "month": lambda c, v: sa.extract("month", c) == v,
        "month_ne": lambda c, v: sa.extract("month", c) != v,
        "month_gt": lambda c, v: sa.extract("month", c) > v,
        "month_ge": lambda c, v: sa.extract("month", c) >= v,
        "month_lt": lambda c, v: sa.extract("month", c) < v,
        "month_le": lambda c, v: sa.extract("month", c) <= v,
        "day": lambda c, v: sa.extract("day", c) == v,
        "day_ne": lambda c, v: sa.extract("day", c) != v,
        "day_gt": lambda c, v: sa.extract("day", c) > v,
        "day_ge": lambda c, v: sa.extract("day", c) >= v,
        "day_lt": lambda c, v: sa.extract("day", c) < v,
        "day_le": lambda c, v: sa.extract("day", c) <= v,
    }

    _base_query: sa.Select

    class Meta:
        model: typing.ClassVar[type[Model]]
        soft_delete: typing.ClassVar[bool] = False
        soft_delete_field: typing.ClassVar[str] = "deleted_at"

    @classmethod
    def _gen_base_query(cls) -> sa.Select:
        return sa.select(cls.Meta.model)

    def _reset_base_query(self):
        self._base_query = self._gen_base_query()

    # TODO: add typings
    @classmethod
    def _update(cls, instance, **kwargs):
        for key, value in kwargs.items():
            setattr(instance, key, value)
        return instance

    @property
    def pk(self) -> str | None:
        meta = sa.inspect(self.Meta.model)
        if not meta:
            return None

        return meta.primary_key[0].name

    def base(self, query: sa.Select) -> typing.Self:
        self._base_query = query
        return self

    def query(self) -> sa.Select:
        return self._base_query

    def filter(self, **kwargs) -> typing.Self:
        return self._filter_or_exclude(False, kwargs)

    def exclude(self, **kwargs) -> typing.Self:
        return self._filter_or_exclude(True, kwargs)

    def limit(self, limit: int | None = None) -> typing.Self:
        self._base_query = self._base_query.limit(limit)
        return self

    def offset(self, offset: int | None = None) -> typing.Self:
        self._base_query = self._base_query.offset(offset)
        return self

    def order_by(self, **kwargs) -> typing.Self:
        for arg, value in kwargs.items():
            if not isinstance(value, bool):
                raise ValueError(f"Argument {arg} value must be boolean.")

            op = sa.asc if value else sa.desc
            nested_path = self._LOADING_SEP in arg
            if nested_path:
                loading, field = arg.rsplit(self._LOADING_SEP, 1)
            else:
                loading = ""
                field = arg

            if loading:
                self.load_related(loading)

                entity = self._find_target_model(loading)
                column = getattr(entity, field, None)
            else:
                column = getattr(self.Meta.model, field, None)

            if column is None:
                raise ValueError(f"Column {field} is not defined.")

            expr: sa.UnaryExpression = op(column)
            self._base_query = self._base_query.order_by(expr)

        return self

    def _find_target_model(self, loading: str):
        model_inspect: orm.Mapper = sa.inspect(self.Meta.model)
        path = loading.split(self._LOADING_SEP)

        curr_relationships = model_inspect.relationships
        curr_entity = model_inspect.entity
        for relation in path:
            relationship = getattr(curr_relationships, relation)
            if not relationship:
                raise ValueError(f"No such relationship: {relation}.")

            curr_entity = relationship.entity.class_
            curr_relationships = relationship.entity.relationships

        return curr_entity

    def _filter_or_exclude(self, negate: bool, kwargs: dict[str, typing.Any]) -> typing.Self:
        def negate_if(exp):
            return exp if not negate else ~exp

        for arg, value in kwargs.items():
            nested_arg = self._LOADING_SEP in arg
            if nested_arg:
                path, token = arg.rsplit(self._LOADING_SEP, 1)
            else:
                token = "exact"  # noqa: S105
                path = arg

            op = self._UNDERSCORE_OPERATORS.get(token)
            if op is None:
                raise ValueError(f"Unsupported operator {token}.")

            nested_path = self._LOADING_SEP in path
            if nested_path:
                loading, field = path.rsplit(self._LOADING_SEP, 1)
            else:
                loading = ""
                field = path

            if loading:
                self.load_related(loading)

                entity = self._find_target_model(loading)
                column = getattr(entity, field, None)
            else:
                column = getattr(self.Meta.model, field, None)

            if column is None:
                raise ValueError(f"Column {field} is not defined.")

            expr = negate_if(op(column, value))
            self._base_query = self._base_query.filter(expr)

        return self

    def _get_load_expression(self, model_inspect: orm.Mapper, loading: str):
        i = loading.find(self._LOADING_SEP)
        relation = loading[:i] if i != -1 else loading

        relationship = getattr(model_inspect.relationships, relation, None)
        if relationship is None:
            raise ValueError(f"No such relationship: {relation}.")

        info = relationship.info
        loading_type = info.get(self._RELATION_LOAD_FIELD)
        if not loading_type:
            raise ValueError(f"Missing type for loading relationship: {relationship}.")

        func = self._LOADING_FUNCS.get(loading_type)
        if not func:
            raise ValueError(f"Unknown loading type: {loading_type}.")

        load_exp = func(relationship)
        if i == -1:
            return load_exp

        next_model_inspect = relationship.entity
        next_loading = loading[i + len(self._LOADING_SEP) :]
        return load_exp.options(self._get_load_expression(next_model_inspect, next_loading))

    def _join_related(
        self,
        model_inspect: orm.Mapper,
        loadings: typing.Iterable[str],
    ) -> None:
        for loading in loadings:
            path = loading.split(self._LOADING_SEP)

            current_entity = model_inspect.entity
            for relation in path:
                relationship = getattr(current_entity, relation, None)
                if relationship is None:
                    raise ValueError(f"No such relationship: {relation}.")

                info = relationship.info

                loading_type = info.get("load")
                if not loading_type:
                    raise ValueError(f"Missing type for loading relationship: {relation}.")

                if loading_type in {
                    RelationLoadingEnum.SELECTIN,
                    RelationLoadingEnum.SUBQUERY,
                }:
                    break

                if relationship is None:
                    raise ValueError(f"Missing relationship: {relation}.")

                self._base_query = self._base_query.outerjoin(relationship)
                current_entity = relationship.entity

    def load_related(
        self,
        *loadings,
    ) -> typing.Self:
        model_inspect: orm.Mapper = sa.inspect(self.Meta.model)
        options = (self._get_load_expression(model_inspect, loading) for loading in loadings)
        self._join_related(model_inspect, loadings)
        self._base_query = self._base_query.options(*options)
        return self


class BaseSqlAlchemyAsyncDAL(BaseSqlAlchemyDAL, BaseAsyncDAL, abc.ABC):
    pass
