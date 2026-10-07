def pairwise_sum(xs: list[int]) -> list[int]:
    """Sums of consecutive pairs."""
    return [a + b for a, b in zip(xs, xs[1:])]
