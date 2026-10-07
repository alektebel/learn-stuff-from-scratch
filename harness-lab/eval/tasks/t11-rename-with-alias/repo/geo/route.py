from geo.distance import calc_dist


def route_length(points: list[tuple[float, float]]) -> float:
    return sum(calc_dist(p, q) for p, q in zip(points, points[1:]))
