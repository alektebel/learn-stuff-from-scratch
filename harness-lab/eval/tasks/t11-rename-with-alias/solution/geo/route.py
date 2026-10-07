from geo.distance import haversine_km


def route_length(points: list[tuple[float, float]]) -> float:
    return sum(haversine_km(p, q) for p, q in zip(points, points[1:]))
