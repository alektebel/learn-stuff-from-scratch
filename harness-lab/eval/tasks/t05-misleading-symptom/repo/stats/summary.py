from stats.group import group_names, group_values


def summarise(rows):
    values = group_values(rows)
    out = []
    for name in group_names(rows):
        vs = values.get(name, [])
        out.append((name, len(vs), round(sum(vs) / len(vs), 2)))
    return out
