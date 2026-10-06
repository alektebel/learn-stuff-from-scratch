from textutils import slugify, truncate


def test_truncate():
    assert truncate("hello", 10) == "hello"
    assert truncate("hello world", 5) == "hell…"


def test_slugify():
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("Ñandú  über") == "nandu-uber"
    assert slugify("!!!") == ""
