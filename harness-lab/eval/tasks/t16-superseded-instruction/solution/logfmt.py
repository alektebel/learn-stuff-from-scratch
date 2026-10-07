from datetime import datetime, timezone


def format_record(level: str, msg: str, ts: datetime) -> str:
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError("ts must be timezone-aware")
    stamp = ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{stamp} [{level.upper()}] {msg}"
