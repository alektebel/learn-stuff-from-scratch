def median(xs: list[float]) -> float:
    if not xs:
        raise ValueError("median of empty list")
    s = sorted(xs)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2
