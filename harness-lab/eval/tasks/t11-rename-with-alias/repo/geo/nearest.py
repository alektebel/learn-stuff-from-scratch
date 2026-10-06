from geo import distance


def nearest(origin, candidates):
    return min(candidates, key=lambda c: distance.calc_dist(origin, c))


def within(origin, candidates, km):
    return [c for c in candidates if distance.calc_dist(origin, c) <= km]
