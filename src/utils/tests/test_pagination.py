import pytest

from utils.pagination import LimitOffsetPagination
from utils.pagination import PageSizePagination


class TestPageSizePagination:
    @pytest.mark.parametrize(
        (
            "page",
            "page_size",
            "expected_page",
            "expected_page_size",
        ),
        [
            (1, 10, 2, 10),
            (2, 10, 3, 10),
        ],
    )
    def test_next(
        self,
        page: int,
        page_size: int,
        expected_page: int,
        expected_page_size: int,
    ) -> None:
        pagination = PageSizePagination(page_size, page)
        pagination.next()

        assert pagination.page == expected_page
        assert pagination.page_size == expected_page_size

    @pytest.mark.parametrize(
        (
            "page",
            "page_size",
            "expected_page",
            "expected_page_size",
        ),
        [
            (1, 10, 1, 10),
            (2, 10, 1, 10),
        ],
    )
    def test_prev(
        self,
        page: int,
        page_size: int,
        expected_page: int,
        expected_page_size: int,
    ) -> None:
        pagination = PageSizePagination(page_size, page)
        pagination.prev()

        assert pagination.page == expected_page
        assert pagination.page_size == expected_page_size

    @pytest.mark.parametrize(
        (
            "page",
            "page_size",
        ),
        [
            (0, 10),
            (-1, 10),
            (1, 0),
            (1, -1),
        ],
    )
    def test_invalid(
        self,
        page: int,
        page_size: int,
    ) -> None:
        with pytest.raises(ValueError, match=r"must be greater than or equal to \d+"):
            _ = PageSizePagination(page_size, page)

    @pytest.mark.parametrize(
        (
            "page_size",
            "page",
            "expected_limit",
            "expected_offset",
        ),
        [
            (10, 1, 10, 0),
            (10, 2, 10, 10),
        ],
    )
    def test_get_limit_offset(
        self,
        page_size: int,
        page: int,
        expected_limit: int,
        expected_offset: int,
    ) -> None:
        pagination = PageSizePagination(page_size, page)
        actual_limit, actual_offset = pagination.get_limit_offset()

        assert actual_limit == expected_limit
        assert actual_offset == expected_offset


class TestLimitOffsetPagination:
    @pytest.mark.parametrize(
        (
            "limit",
            "offset",
            "expected_limit",
            "expected_offset",
        ),
        [
            (10, 0, 10, 10),
            (10, 10, 10, 20),
        ],
    )
    def test_next(
        self,
        limit: int,
        offset: int,
        expected_limit: int,
        expected_offset: int,
    ) -> None:
        pagination = LimitOffsetPagination(limit, offset)
        pagination.next()

        assert pagination.limit == expected_limit
        assert pagination.offset == expected_offset

    @pytest.mark.parametrize(
        (
            "limit",
            "offset",
            "expected_limit",
            "expected_offset",
        ),
        [
            (10, 0, 10, 0),
            (10, 10, 10, 0),
        ],
    )
    def test_prev(
        self,
        limit: int,
        offset: int,
        expected_limit: int,
        expected_offset: int,
    ) -> None:
        pagination = LimitOffsetPagination(limit, offset)
        pagination.prev()

        assert pagination.limit == expected_limit
        assert pagination.offset == expected_offset

    @pytest.mark.parametrize(
        (
            "limit",
            "offset",
        ),
        [
            (0, 0),
            (-1, 0),
            (10, -1),
        ],
    )
    def test_invalid(
        self,
        limit: int,
        offset: int,
    ) -> None:
        with pytest.raises(ValueError, match=r"must be greater than or equal to \d+"):
            _ = LimitOffsetPagination(limit, offset)

    @pytest.mark.parametrize(
        (
            "limit",
            "offset",
            "expected_limit",
            "expected_offset",
        ),
        [
            (10, 0, 10, 0),
            (10, 10, 10, 10),
        ],
    )
    def test_get_limit_offset(
        self,
        limit: int,
        offset: int,
        expected_limit: int,
        expected_offset: int,
    ) -> None:
        pagination = LimitOffsetPagination(limit, offset)
        actual_limit, actual_offset = pagination.get_limit_offset()

        assert actual_limit == expected_limit
        assert actual_offset == expected_offset
