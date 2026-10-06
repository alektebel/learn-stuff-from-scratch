from geo import distance


def nearest(origin, candidates):
    return min(candidates, key=lambda c: distance.haversine_km(origin, c))


def within(origin, candidates, km):
    return [c for c in candidates if distance.haversine_km(origin, c) <= km]
