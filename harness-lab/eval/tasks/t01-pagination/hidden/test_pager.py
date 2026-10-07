import pytest
from pager import paginate, total_pages


def test_first_page_starts_at_first_item():
    assert paginate(list(range(10)), 1, 3) == [0, 1, 2]


def test_partial_last_page():
    assert total_pages(10, 3) == 4
    assert paginate(list(range(10)), 4, 3) == [9]


def test_exact_multiple():
    assert total_pages(9, 3) == 3
    assert paginate(list(range(9)), 3, 3) == [6, 7, 8]


def test_all_pages_cover_items_once():
    items = list(range(23))
    got = [x for p in range(1, total_pages(23, 5) + 1) for x in paginate(items, p, 5)]
    assert got == items


@pytest.mark.parametrize("page", [0, 5, -1])
def test_out_of_range(page):
    with pytest.raises(ValueError):
        paginate(list(range(10)), page, 3)


def test_empty():
    assert total_pages(0, 3) == 0
    with pytest.raises(ValueError):
        paginate([], 1, 3)
