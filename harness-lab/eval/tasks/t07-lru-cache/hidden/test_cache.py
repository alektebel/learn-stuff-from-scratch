import pytest
from cache import Cache


def test_default_capacity():
    c = Cache()
    for i in range(200):
        c.set(i, i)
    assert len(c) == 128 and c.evictions == 72


def test_lru_order_get_counts_as_use():
    c = Cache(capacity=2)
    c.set("a", 1)
    c.set("b", 2)
    assert c.get("a") == 1
    c.set("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1 and c.get("c") == 3


def test_set_existing_counts_as_use_and_does_not_evict():
    c = Cache(capacity=2)
    c.set("a", 1)
    c.set("b", 2)
    c.set("a", 10)
    assert c.evictions == 0
    c.set("c", 3)
    assert c.get("b") is None and c.get("a") == 10


def test_counters():
    c = Cache(capacity=1)
    c.get("x")
    c.set("x", 1)
    c.get("x")
    c.set("y", 2)
    assert (c.hits, c.misses, c.evictions) == (1, 1, 1)


@pytest.mark.parametrize("cap", [0, -1, 1.5, "3"])
def test_invalid_capacity(cap):
    with pytest.raises(ValueError):
        Cache(capacity=cap)
