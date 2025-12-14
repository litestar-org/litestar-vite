"""Tests for Inertia types module."""

from dataclasses import dataclass

from litestar_vite.inertia.helpers import extract_pagination_scroll_props, is_pagination_container
from litestar_vite.inertia.types import to_camel_case


def test_to_camel_case_simple() -> None:
    """Test simple snake_case conversion."""
    assert to_camel_case("hello_world") == "helloWorld"


def test_to_camel_case_multiple_underscores() -> None:
    """Test multiple underscores in snake_case."""
    assert to_camel_case("deep_merge_props") == "deepMergeProps"


def test_to_camel_case_no_underscore() -> None:
    """Test string without underscore stays the same."""
    assert to_camel_case("hello") == "hello"


def test_to_camel_case_single_char() -> None:
    """Test single character conversion."""
    assert to_camel_case("a_b") == "aB"


# Pagination container detection tests


@dataclass
class MockOffsetPagination:
    """Mock OffsetPagination for testing."""

    items: list[str]
    limit: int
    offset: int
    total: int


@dataclass
class MockClassicPagination:
    """Mock ClassicPagination for testing."""

    items: list[str]
    page_size: int
    current_page: int
    total_pages: int


def test_is_pagination_container_offset_style() -> None:
    """Test detection of OffsetPagination-style containers."""
    pagination = MockOffsetPagination(items=["a", "b"], limit=10, offset=0, total=50)
    assert is_pagination_container(pagination) is True


def test_is_pagination_container_classic_style() -> None:
    """Test detection of ClassicPagination-style containers."""
    pagination = MockClassicPagination(items=["a", "b"], page_size=10, current_page=1, total_pages=5)
    assert is_pagination_container(pagination) is True


def test_is_pagination_container_regular_value() -> None:
    """Test that regular values are not detected as pagination containers."""
    assert is_pagination_container(["a", "b", "c"]) is False
    assert is_pagination_container({"items": ["a"]}) is False
    assert is_pagination_container("string") is False
    assert is_pagination_container(None) is False


# Pagination extraction tests - OffsetPagination style


def test_extract_pagination_first_page_offset() -> None:
    """Test extraction from OffsetPagination on first page."""
    pagination = MockOffsetPagination(items=["a", "b", "c"], limit=10, offset=0, total=50)
    items, scroll = extract_pagination_scroll_props(pagination)

    assert items == ["a", "b", "c"]
    assert scroll is not None
    assert scroll.current_page == 1
    assert scroll.previous_page is None
    assert scroll.next_page == 2


def test_extract_pagination_middle_page_offset() -> None:
    """Test extraction from OffsetPagination on middle page."""
    pagination = MockOffsetPagination(items=["d", "e", "f"], limit=10, offset=20, total=50)
    items, scroll = extract_pagination_scroll_props(pagination)

    assert items == ["d", "e", "f"]
    assert scroll is not None
    assert scroll.current_page == 3  # offset=20, limit=10 -> page 3
    assert scroll.previous_page == 2
    assert scroll.next_page == 4


def test_extract_pagination_last_page_offset() -> None:
    """Test extraction from OffsetPagination on last page."""
    pagination = MockOffsetPagination(items=["j"], limit=10, offset=40, total=50)
    items, scroll = extract_pagination_scroll_props(pagination)

    assert items == ["j"]
    assert scroll is not None
    assert scroll.current_page == 5  # offset=40, limit=10 -> page 5
    assert scroll.previous_page == 4
    assert scroll.next_page is None  # 50 total, limit 10 = 5 pages, on page 5


# Pagination extraction tests - ClassicPagination style


def test_extract_pagination_first_page_classic() -> None:
    """Test extraction from ClassicPagination on first page."""
    pagination = MockClassicPagination(items=["a", "b", "c"], page_size=10, current_page=1, total_pages=4)
    items, scroll = extract_pagination_scroll_props(pagination)

    assert items == ["a", "b", "c"]
    assert scroll is not None
    assert scroll.current_page == 1
    assert scroll.previous_page is None
    assert scroll.next_page == 2


def test_extract_pagination_middle_page_classic() -> None:
    """Test extraction from ClassicPagination on middle page."""
    pagination = MockClassicPagination(items=["d", "e", "f"], page_size=10, current_page=2, total_pages=4)
    items, scroll = extract_pagination_scroll_props(pagination)

    assert items == ["d", "e", "f"]
    assert scroll is not None
    assert scroll.current_page == 2
    assert scroll.previous_page == 1
    assert scroll.next_page == 3


def test_extract_pagination_last_page_classic() -> None:
    """Test extraction from ClassicPagination on last page."""
    pagination = MockClassicPagination(items=["j"], page_size=10, current_page=4, total_pages=4)
    items, scroll = extract_pagination_scroll_props(pagination)

    assert items == ["j"]
    assert scroll is not None
    assert scroll.current_page == 4
    assert scroll.previous_page == 3
    assert scroll.next_page is None


def test_extract_pagination_single_page() -> None:
    """Test extraction with single page."""
    pagination = MockClassicPagination(items=["a", "b", "c"], page_size=10, current_page=1, total_pages=1)
    items, scroll = extract_pagination_scroll_props(pagination)

    assert items == ["a", "b", "c"]
    assert scroll is not None
    assert scroll.current_page == 1
    assert scroll.previous_page is None
    assert scroll.next_page is None


def test_extract_pagination_custom_page_param() -> None:
    """Test extraction with custom page parameter name."""
    pagination = MockClassicPagination(items=["a", "b"], page_size=10, current_page=1, total_pages=5)
    _, scroll = extract_pagination_scroll_props(pagination, page_param="cursor")

    assert scroll is not None
    assert scroll.page_name == "cursor"


def test_extract_pagination_non_container() -> None:
    """Test extraction from non-pagination values returns value unchanged."""
    items, scroll = extract_pagination_scroll_props(["a", "b", "c"])

    assert items == ["a", "b", "c"]
    assert scroll is None


def test_extract_pagination_with_typed_items() -> None:
    """Test that extraction works with typed items."""

    @dataclass
    class User:
        id: int
        name: str

    users = [User(id=1, name="Alice"), User(id=2, name="Bob")]

    @dataclass
    class UserPagination:
        items: list[User]
        page_size: int
        current_page: int
        total_pages: int

    pagination = UserPagination(items=users, page_size=10, current_page=1, total_pages=10)
    extracted_items, scroll = extract_pagination_scroll_props(pagination)

    assert len(extracted_items) == 2
    assert extracted_items[0].name == "Alice"
    assert scroll is not None
    assert scroll.current_page == 1


# =====================================================
# ScrollPagination Tests
# =====================================================


def test_scroll_pagination_direct_construction() -> None:
    """Test ScrollPagination can be constructed directly."""
    from litestar_vite.inertia.types import ScrollPagination

    pagination: ScrollPagination[str] = ScrollPagination(items=["a", "b", "c"], total=100, limit=10, offset=20)

    assert pagination.items == ["a", "b", "c"]
    assert pagination.total == 100
    assert pagination.limit == 10
    assert pagination.offset == 20


def test_scroll_pagination_create_from_offset() -> None:
    """Test ScrollPagination.create_from with OffsetPagination-style data."""
    from litestar_vite.inertia.types import ScrollPagination

    offset_pagination = MockOffsetPagination(items=["x", "y"], limit=10, offset=30, total=50)
    scroll: ScrollPagination[str] = ScrollPagination.create_from(offset_pagination)

    assert scroll.items == ["x", "y"]
    assert scroll.total == 50
    assert scroll.limit == 10
    assert scroll.offset == 30


def test_scroll_pagination_create_from_classic() -> None:
    """Test ScrollPagination.create_from with ClassicPagination-style data."""
    from litestar_vite.inertia.types import ScrollPagination

    classic_pagination = MockClassicPagination(items=["a", "b"], page_size=10, current_page=3, total_pages=5)
    scroll: ScrollPagination[str] = ScrollPagination.create_from(classic_pagination)

    assert scroll.items == ["a", "b"]
    assert scroll.limit == 10
    assert scroll.offset == 20  # (3-1) * 10 = 20
    assert scroll.total == 50  # 5 * 10 = 50


def test_scroll_pagination_is_pagination_container() -> None:
    """Test ScrollPagination is recognized as a pagination container."""
    from litestar_vite.inertia.types import ScrollPagination

    pagination: ScrollPagination[str] = ScrollPagination(items=["a"], total=10, limit=5, offset=0)

    assert is_pagination_container(pagination)


def test_scroll_pagination_works_with_extract_scroll_props() -> None:
    """Test ScrollPagination works with extract_pagination_scroll_props."""
    from litestar_vite.inertia.types import ScrollPagination

    pagination: ScrollPagination[str] = ScrollPagination(items=["a", "b"], total=50, limit=10, offset=20)
    items, scroll = extract_pagination_scroll_props(pagination)

    assert items == ["a", "b"]
    assert scroll is not None
    assert scroll.current_page == 3  # offset=20, limit=10 -> page 3
    assert scroll.previous_page == 2
    assert scroll.next_page == 4
