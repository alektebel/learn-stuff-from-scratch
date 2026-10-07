from datetime import timedelta

import pytest
from durations import parse_duration


@pytest.mark.parametrize("text,expected", [
    ("1h30m", timedelta(hours=1, minutes=30)),
    ("2d", timedelta(days=2)),
    ("90m", timedelta(minutes=90)),
    ("0s", timedelta(0)),
    ("500ms", timedelta(milliseconds=500)),
    ("1m500ms", timedelta(minutes=1, milliseconds=500)),
    ("1s5ms", timedelta(seconds=1, milliseconds=5)),
    ("1d2h3m4s5ms", timedelta(days=1, hours=2, minutes=3, seconds=4, milliseconds=5)),
    ("007s", timedelta(seconds=7)),
])
def test_valid(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("text", [
    "", "h", "10", "1.5h", "-5m", "+5m", "1h 30m", " 1h", "1h ", "1H",
    "30m1h", "1m1m", "1s1m", "5ms1s", "1x", "1hm", "1h30", "ms",
])
def test_invalid(text):
    with pytest.raises(ValueError):
        parse_duration(text)
