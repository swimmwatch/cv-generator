import abc
import dataclasses
import typing
from collections.abc import AsyncIterator
from collections.abc import Iterator


class BasePagination(abc.ABC):
    @abc.abstractmethod
    def get_limit_offset(self) -> tuple[int, int]:
        pass

    @abc.abstractmethod
    def next(self) -> None:
        pass

    @abc.abstractmethod
    def prev(self) -> None:
        pass


class PageSizePagination(BasePagination):
    def __init__(self, page_size: int = 10, page: int = 1) -> None:
        if page_size < 1:
            raise ValueError("Page size must be greater than or equal to 1.")

        if page < 1:
            raise ValueError("Page must be greater than or equal to 1.")

        self._page_size = page_size
        self._page = page

    @property
    def page_size(self) -> int:
        return self._page_size

    @property
    def page(self) -> int:
        return self._page

    def get_limit_offset(self) -> tuple[int, int]:
        return self._page_size, (self._page - 1) * self._page_size

    def next(self) -> None:
        self._page += 1

    def prev(self) -> None:
        if self._page == 1:
            return

        self._page -= 1


class LimitOffsetPagination(BasePagination):
    def __init__(self, limit: int = 10, offset: int = 0) -> None:
        if limit < 1:
            raise ValueError("Limit must be greater than or equal to 1.")

        if offset < 0:
            raise ValueError("Offset must be greater than or equal to 0.")

        self._limit = limit
        self._offset = offset

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def offset(self) -> int:
        return self._offset

    def get_limit_offset(self) -> tuple[int, int]:
        return self._limit, self._offset

    def next(self):
        self._offset += self._limit

    def prev(self):
        if self._offset == 0:
            return

        self._offset -= self._limit


@dataclasses.dataclass
class PaginationPoint:
    count: int
    has_next: bool
    pagination: BasePagination


class BasePaginationCursor(abc.ABC, Iterator):
    @abc.abstractmethod
    def next(self) -> tuple[PaginationPoint, typing.Iterable]:
        pass

    @abc.abstractmethod
    def prev(self) -> tuple[PaginationPoint, typing.Iterable]:
        pass


class BaseAsyncPaginationCursor(abc.ABC, AsyncIterator):
    @abc.abstractmethod
    async def next(self) -> tuple[PaginationPoint, typing.Iterable]:
        pass

    @abc.abstractmethod
    async def prev(self) -> tuple[PaginationPoint, typing.Iterable]:
        pass
