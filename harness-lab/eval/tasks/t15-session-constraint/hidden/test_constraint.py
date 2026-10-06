import inspect
from decimal import Decimal

import billing
import pytest


def new_public_functions():
    return [n for n, f in inspect.getmembers(billing, inspect.isfunction)
            if f.__module__ == "billing" and not n.startswith("_") and n != "calc_monthly_rate"]


def the_function():
    fns = new_public_functions()
    assert len(fns) == 1, f"expected exactly one new public function, got {fns}"
    return getattr(billing, fns[0])


def test_prefix_rule_from_first_turn():
    fns = new_public_functions()
    assert fns and all(n.startswith("calc_") for n in fns), fns


def test_decimal_rule_and_values():
    f = the_function()
    assert f("pro", 3) == Decimal("73.50") and isinstance(f("pro", 3), Decimal)
    assert f("basic", 12) == Decimal("107.89")   # 119.88 * 0.9 = 107.892
    assert f("team", 24) == Decimal("1706.40")


def test_errors():
    f = the_function()
    with pytest.raises(KeyError):
        f("gold", 1)
    with pytest.raises(ValueError):
        f("pro", 0)


def test_no_float_in_source():
    src = inspect.getsource(the_function())
    assert "float(" not in src
