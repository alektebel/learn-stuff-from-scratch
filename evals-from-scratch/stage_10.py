"""Evals From Scratch — stage 10: the gate, and the report you can diff

DESIGN DECISION — the mean does not excuse a broken slice.
    A candidate that gains three points overall while halving the pass rate for
    one enterprise tenant is a regression, and the aggregate number is
    precisely the thing that hides it. Floors are per slice, and a breach
    decides the run whatever the average says. This is the guide's warning —
    "a single aggregate number over mirrored traffic is the failure mode" —
    implemented as a rule rather than as a value.

DESIGN DECISION — three outcomes, and the reasons are part of the result.
    pass / regress / inconclusive, with the reasons that produced it: which
    slice breached, which interval straddled zero, how many items were dropped
    for having no partner. A gate whose output is a bare boolean cannot be
    reviewed, and one that never says "inconclusive" is a gate that ships noise
    as often as it blocks it.

TODO: implement (rows are dicts with "id", "passed" (bool), "latency_ms", and a
slice key such as "tenant")

    gate(baseline, candidate, key="tenant", floors=None, alpha=0.05, seed=0) -> dict
        Match the two runs by "id" (a run is a list of rows). Rows present on
        only one side are dropped and COUNTED, never paired up by position.
        Returns:
            {"decision": "pass" | "regress" | "inconclusive",
             "reasons": [str, ...],
             "n_paired": int, "n_dropped": int,
             "overall": {"n", "baseline", "candidate", "diff", "lo", "hi"},
             "slices": {name: {"n", "baseline", "candidate", "diff",
                               "breach": bool}}}
        Decision, in this order:
          1. any slice listed in `floors` whose candidate pass rate is BELOW
             its floor  -> "regress", reason naming the slice, its rate and the
             floor. A floor for a slice that does not appear in the candidate
             at all is a breach too: a tenant that vanished has not met it;
          2. the paired interval entirely below zero -> "regress";
          3. entirely above zero -> "pass";
          4. otherwise -> "inconclusive", with a reason that says the interval
             contains zero.
        The rates are computed over the PAIRED rows only, so a run that added
        items is not compared against a different denominator. `diff` is the
        candidate minus the baseline, in `overall` and in every slice, so a
        positive number always means the candidate is better.
        With fewer than 2 paired rows there is no interval: say "inconclusive"
        (or "regress" when a floor is breached — that rule does not need the
        interval) and put the counts in the reasons rather than returning a
        confident number from one item.

    report_json(result) -> str
        A deterministic, diffable rendering: sorted keys, floats rounded to 4
        decimals, one key per line. Two runs with the same numbers must produce
        byte-identical output, or a CI diff shows noise instead of change.
"""


def gate(baseline, candidate, key="tenant", floors=None, alpha=0.05, seed=0):
    raise NotImplementedError("stage 10: implement gate()")


def report_json(result):
    raise NotImplementedError("stage 10: implement report_json()")
