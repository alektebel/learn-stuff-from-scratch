from collections.abc import Iterable, Iterator


def pairwise_sum(xs: list[int]) -> list[int]:
    """Sums of consecutive pairs."""
    return [a + b for a, b in zip(xs, xs[1:])]


def chunks(xs: Iterable, n: int) -> Iterator[list]:
    """Consecutive lists of length n; the last may be shorter."""
    if n < 1:
        raise ValueError("n must be >= 1")
    buf = []
    for x in xs:
        buf.append(x)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf
