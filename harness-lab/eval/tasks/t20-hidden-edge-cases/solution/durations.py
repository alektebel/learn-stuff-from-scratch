import re
from datetime import timedelta

_UNITS = ["d", "h", "m", "s", "ms"]
_SCALE = {"d": timedelta(days=1), "h": timedelta(hours=1), "m": timedelta(minutes=1),
          "s": timedelta(seconds=1), "ms": timedelta(milliseconds=1)}
# "ms" must be tried before "m", otherwise "500ms" tokenises as 500m + "s"
_COMPONENT = re.compile(r"([0-9]+)(ms|d|h|m|s)")


def parse_duration(text: str) -> timedelta:
    pos, last_rank, total = 0, -1, timedelta()
    if not text:
        raise ValueError("empty duration")
    while pos < len(text):
        m = _COMPONENT.match(text, pos)
        if m is None:
            raise ValueError(f"invalid duration {text!r} at position {pos}")
        value, unit = int(m.group(1)), m.group(2)
        rank = _UNITS.index(unit)
        if rank <= last_rank:
            raise ValueError(f"unit {unit!r} out of order or repeated in {text!r}")
        last_rank = rank
        total += value * _SCALE[unit]
        pos = m.end()
    return total
