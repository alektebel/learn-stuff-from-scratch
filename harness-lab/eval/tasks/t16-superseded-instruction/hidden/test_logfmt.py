from datetime import datetime, timedelta, timezone

import pytest
from logfmt import format_record


def test_uses_corrected_format():
    ts = datetime(2025, 1, 31, 9, 5, 0, 123456, tzinfo=timezone.utc)
    assert format_record("error", "disk full", ts) == "2025-01-31T09:05:00Z [ERROR] disk full"


def test_converts_to_utc():
    madrid = timezone(timedelta(hours=1))
    ts = datetime(2025, 1, 1, 0, 30, tzinfo=madrid)
    assert format_record("Info", "x", ts) == "2024-12-31T23:30:00Z [INFO] x"


def test_naive_rejected():
    with pytest.raises(ValueError):
        format_record("info", "x", datetime(2025, 1, 1))
