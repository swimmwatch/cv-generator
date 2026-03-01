import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from infra.db.base import Model
from infra.db.types import ModelType
from infra.db.utils.dal.base import BaseSqlAlchemyAsyncDAL
from utils.pagination import BaseAsyncPaginationCursor
from utils.pagination import BasePagination
from utils.pagination import PaginationPoint

if typing.TYPE_CHECKING:
    from utils.dal import BaseAsyncDAL


class AsyncPaginationCursor(BaseAsyncPaginationCursor):
    def __init__(self, dal: "BaseAsyncDAL", pagination: BasePagination) -> None:
        self._dal = dal
        self._pagination = pagination

    async def has_next(self) -> tuple[bool, int]:
        limit, offset = self._pagination.get_limit_offset()
        count = await self._dal.count()
        return offset < count, count

    # TODO: use correct typing for "items" argument
    async def next(self) -> tuple[PaginationPoint, typing.Iterable]:
        has_next, count = await self.has_next()
        point = PaginationPoint(count, has_next, self._pagination)

        if not has_next:
            return point, iter([])

        limit, offset = self._pagination.get_limit_offset()
        items: list[Model] = await self._dal.limit(limit).offset(offset).scalars()
        self._pagination.next()

        return point, items

    # TODO: use correct typing for "items" argument
    async def prev(self):
        raise NotImplementedError

    def __aiter__(self):
        return self

    async def __anext__(self) -> tuple[PaginationPoint, typing.Iterable]:
        point, items = await self.next()

        if not point.has_next:
            raise StopAsyncIteration

        return point, items


class SqlAlchemyAsyncDAL(BaseSqlAlchemyAsyncDAL):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._base_query: sa.Select = self._gen_base_query()

    async def first(self):
        res = await self._session.execute(self._base_query)
        self._reset_base_query()
        return res.scalar_one_or_none()

    async def all(self) -> typing.Sequence[sa.Row]:
        res = await self._session.execute(self._base_query)
        self._reset_base_query()
        return res.all()

    async def scalars(self) -> list[ModelType]:
        res = await self._session.execute(self._base_query)
        self._reset_base_query()
        return list(res.scalars())

    def paginate(self, pagination: BasePagination) -> AsyncPaginationCursor:
        return AsyncPaginationCursor(self, pagination)

    async def count(self) -> int:
        subquery = self._base_query.limit(None).offset(None).subquery()
        count_query = sa.select(sa.func.count()).select_from(subquery)
        res = await self._session.execute(count_query)
        count = res.scalar()
        self._reset_base_query()
        return typing.cast(int, count)

    # TODO: add return typing
    async def create_one(self, **kwargs):
        instance = self.Meta.model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        self._reset_base_query()
        return instance

    # TODO: add return typing
    async def update_instance(self, instance, **kwargs):
        updated_instance = self._update(instance, **kwargs)
        await self._session.flush()
        self._reset_base_query()
        return updated_instance

    # TODO: add return typing
    async def update_or_create(self, **kwargs) -> typing.Callable:
        async def update(**inner_kwargs):
            instance = await self.filter(**kwargs).first()

            if not instance:
                params = {**kwargs, **inner_kwargs}
                if self.pk and self.pk in params:
                    params.pop(self.pk)

                return await self.create_one(**params)

            instance = await self.update_instance(instance, **inner_kwargs)

            return instance

        return update

    async def get_or_create(self, **kwargs) -> tuple[ModelType, bool]:
        instance = await self.first()
        if instance:
            return instance, False

        await self.create_one(**kwargs)

        instance = await self.first()
        return instance, True

    async def update(self, **kwargs: typing.Any) -> int:
        stmt = sa.update(self.Meta.model).values(**kwargs)

        if self._base_query.whereclause is not None:
            stmt = stmt.where(self._base_query.whereclause)

        res = await self._session.execute(stmt)
        self._reset_base_query()

        return res.rowcount  # type: ignore[attr-defined]

    async def _soft_delete(self) -> int:
        query = {self.Meta.soft_delete_field: sa.func.now()}  # TODO: calculate the value depends on the field type
        return await self._toggle(**query)

    async def _hard_delete(self) -> int:
        stmt = sa.delete(self.Meta.model)

        if self._base_query.whereclause is not None:
            stmt = stmt.where(self._base_query.whereclause)

        res = await self._session.execute(stmt)
        self._reset_base_query()
        return res.rowcount  # type: ignore[attr-defined]

    async def delete(self) -> int:
        """
        Deletes the records from the database.
        If the model has soft delete enabled, it will set the `soft_delete_field` field.
        """

        if self.Meta.soft_delete:
            res = await self._soft_delete()
        else:
            res = await self._hard_delete()

        return res

    async def _toggle(self, **query: typing.Any) -> int:
        assert self.Meta.soft_delete, "Model cannot be soft deleted."
        return await self.update(**query)

    async def undelete(self) -> int:
        query = {self.Meta.soft_delete_field: None}  # TODO: calculate the value depends on the field type
        return await self._toggle(**query)
