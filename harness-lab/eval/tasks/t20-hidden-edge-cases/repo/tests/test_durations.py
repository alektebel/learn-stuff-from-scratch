from datetime import timedelta

from durations import parse_duration


def test_simple():
    assert parse_duration("1h30m") == timedelta(hours=1, minutes=30)
    assert parse_duration("45s") == timedelta(seconds=45)
