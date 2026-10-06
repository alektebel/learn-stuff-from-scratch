import pytest
from orders import Order


def test_instances_do_not_share_lines():
    a = Order("ana")
    a.add("x", 1)
    b = Order("ana")
    assert b.lines == []


def test_passed_list_is_not_aliased():
    src = [("x", 1)]
    o = Order("ana", src)
    o.add("y", 2)
    assert src == [("x", 1)]


def test_merge_is_pure():
    a, b = Order("ana"), Order("ana")
    a.add("x", 1)
    b.add("y", 2)
    m = a.merge(b)
    assert m is not a and m is not b
    assert m.total_qty() == 3
    assert a.lines == [("x", 1)] and b.lines == [("y", 2)]
    m.add("z", 5)
    assert a.total_qty() == 1 and b.total_qty() == 2


def test_merge_rejects_other_customer():
    with pytest.raises(ValueError):
        Order("ana").merge(Order("bob"))
