"""Version ordering following SemVer 2.0.0 precedence (spec section 11):

1. Compare MAJOR, MINOR, PATCH numerically.
2. A version with a pre-release has LOWER precedence than the same version without one.
3. Pre-releases compare identifier by identifier, left to right (dot-separated):
   - identifiers of only digits compare numerically;
   - other identifiers compare lexically in ASCII order;
   - a numeric identifier has lower precedence than a non-numeric one;
   - if all shared identifiers are equal, the version with MORE identifiers is greater.
4. Build metadata (after "+") is ignored for precedence.
"""


def _ident(part: str):
    return (0, int(part), "") if part.isdigit() else (1, 0, part)


def sort_key(version: str):
    core, _, _build = version.partition("+")
    core, _, pre = core.partition("-")
    major, minor, patch = (int(x) for x in core.split("."))
    if not pre:
        return (major, minor, patch, 1, ())
    return (major, minor, patch, 0, tuple(_ident(p) for p in pre.split(".")))


def is_newer(a: str, b: str) -> bool:
    return sort_key(a) > sort_key(b)


def latest(versions: list[str]) -> str:
    return max(versions, key=sort_key)
