from collections import defaultdict

from stats.load import normalise_group


def group_values(rows):
    groups = defaultdict(list)
    for g, v in rows:
        groups[g].append(v)
    return groups


def group_names(rows):
    # names as they appear in the raw file, normalised for display
    return sorted({normalise_group(g.strip()) for g, _ in rows})
