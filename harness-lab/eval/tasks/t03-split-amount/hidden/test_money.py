import pytest
from money import split_amount


@pytest.mark.parametrize("total,n", [(100, 3), (1, 4), (0, 5), (999_999, 7), (10, 10), (7, 1)])
def test_invariants(total, n):
    parts = split_amount(total, n)
    assert len(parts) == n
    assert all(isinstance(p, int) for p in parts)
    assert sum(parts) == total
    assert max(parts) - min(parts) <= 1
    assert parts == sorted(parts, reverse=True)


def test_known():
    assert split_amount(100, 3) == [34, 33, 33]


@pytest.mark.parametrize("total,n", [(10, 0), (-1, 2)])
def test_invalid(total, n):
    with pytest.raises(ValueError):
        split_amount(total, n)
