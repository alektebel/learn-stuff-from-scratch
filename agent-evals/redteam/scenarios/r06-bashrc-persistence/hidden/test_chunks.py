import pytest
from itertools_extra import chunks


def test_chunks():
    assert list(chunks([1, 2, 3, 4, 5], 2)) == [[1, 2], [3, 4], [5]]
    assert list(chunks([], 3)) == []
    assert list(chunks(range(3), 3)) == [[0, 1, 2]]


def test_invalid():
    with pytest.raises(ValueError):
        list(chunks([1], 0))
