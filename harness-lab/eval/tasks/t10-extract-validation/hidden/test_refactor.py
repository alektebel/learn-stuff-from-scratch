import ast
import pathlib

import pytest
from handlers import change_email, invite, register
from validators import validate_email


def test_validate_email():
    assert validate_email("  Ana@Example.COM ") == "ana@example.com"
    with pytest.raises(ValueError, match=r"invalid email: 'nope'"):
        validate_email("nope")


def test_behaviour_unchanged():
    assert register("a", " A@B.io") == {"name": "a", "email": "a@b.io"}
    assert change_email({"name": "a", "email": "x@y.io"}, "Z@Y.io")["email"] == "z@y.io"
    assert invite({"email": "me@x.io"}, ["ME@x.io", "you@x.io "]) == ["you@x.io"]
    for fn, args in [(register, ("a", "bad")), (change_email, ({}, "bad@")), (invite, ({"email": ""}, ["@x.io"]))]:
        with pytest.raises(ValueError, match="invalid email"):
            fn(*args)


def test_handlers_have_no_regex_and_use_helper():
    src = pathlib.Path("/work/handlers.py").read_text()
    tree = ast.parse(src)
    imported = {a.name for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    assert "re" not in imported
    assert "fullmatch" not in src and "[a-z" not in src
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", getattr(n.func, "attr", None)) == "validate_email"]
    assert len(calls) >= 3
