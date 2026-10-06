from textutils import truncate


def test_truncate():
    assert truncate("hello", 10) == "hello"
    assert truncate("hello world", 5) == "hell…"
