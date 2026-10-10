"""Evals From Scratch — stage 9: ten configs, one winner, no correction

SOLUTION. Holm's step-down in five lines: multiply the i-th smallest by the
number of tests still standing, then force the result through a running maximum
so the adjusted values stay monotone in the sorted p-values.
"""


def holm(p_values):
    values = [float(p) for p in p_values]
    m = len(values)
    if m == 0:
        return []
    adjusted = [0.0] * m
    running = 0.0
    for step, index in enumerate(sorted(range(m), key=lambda i: values[i])):
        running = max(running, min(1.0, values[index] * (m - step)))
        adjusted[index] = running
    return adjusted


def significant(p_values, alpha=0.05):
    values = [float(p) for p in p_values]
    m = len(values)
    if m == 0:
        return {"rejected": [], "adjusted": [], "thresholds": []}

    order = sorted(range(m), key=lambda i: values[i])
    thresholds = [0.0] * m
    rejected = [False] * m
    for step, index in enumerate(order):
        thresholds[index] = alpha / (m - step)

    for step, index in enumerate(order):
        if values[index] <= alpha / (m - step):
            rejected[index] = True
        else:
            break                       # step-down: the rest are not rejected

    return {"rejected": rejected, "adjusted": holm(values),
            "thresholds": thresholds}
