import ast
import pathlib

import pytest
from inventory import Inventory
from report import low_stock


def test_independent_instances():
    a, b = Inventory(), Inventory()
    a.add("x", 5)
    assert b.quantity("x") == 0 and a.quantity("x") == 5


def test_behaviour():
    inv = Inventory()
    inv.add("b", 3)
    inv.add("a", 1)
    inv.remove("b", 3)
    assert inv.skus() == ["a"]
    with pytest.raises(KeyError, match="insufficient stock for a: have 1, need 2"):
        inv.remove("a", 2)
    with pytest.raises(ValueError):
        inv.add("a", 0)


def test_low_stock():
    inv = Inventory()
    inv.add("a", 1)
    inv.add("b", 10)
    assert low_stock(inv, 5) == ["a"]


def test_no_module_state():
    tree = ast.parse(pathlib.Path("/work/inventory.py").read_text())
    top_funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    top_assigns = [n for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))]
    assert top_funcs == [] and top_assigns == []
