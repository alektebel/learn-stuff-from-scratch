import re

_RX = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def parse_semver(tag: str) -> tuple[int, int, int]:
    m = _RX.fullmatch(tag)
    if not m:
        raise ValueError(f"not a version: {tag!r}")
    return tuple(int(g) for g in m.groups())
