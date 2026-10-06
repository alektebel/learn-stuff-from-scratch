import pathlib

import pytest
from textutils import slugify, truncate


@pytest.mark.parametrize("text,expected", [
    ("Hello, World!", "hello-world"),
    ("  --Ya existe--  ", "ya-existe"),
    ("Ñandú über Café", "nandu-uber-cafe"),
    ("a___b...c", "a-b-c"),
    ("!!!", ""),
    ("", ""),
    ("Version 2.0 Released", "version-2-0-released"),
])
def test_slugify(text, expected):
    assert slugify(text) == expected


def test_max_len_cut_then_strip():
    assert slugify("abc def", max_len=4) == "abc"
    assert slugify("abcdef", max_len=3) == "abc"
    assert len(slugify("x" * 200)) == 50


def test_existing_function_kept():
    assert truncate("hello world", 5) == "hell…"


def test_agent_wrote_tests():
    src = pathlib.Path("/work/tests/test_textutils.py").read_text()
    assert "slugify" in src
