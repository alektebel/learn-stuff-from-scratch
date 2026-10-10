"""Benchmark From Scratch (Mus) — stage 9 solution: which rows may be published,
and the leaderboard built from them.

The reasoning lives in `stage_09.py`'s docstring; this file is the
implementation. One sentence each:

    * the fallback ratio divides by `llm_turns + fallbacks` — the model's own
      decisions plus the turns the fallback machinery made for it — because
      `turns` counts the baseline seats too;
    * the gate reads the row and only the row, and the leaderboard counts what
      it rejected (`degraded`) instead of forgetting it;
    * every row is added twice, once per label, with side A on the FOR side for
      `label_a` and on the AGAINST side for `label_b`;
    * `piedras_per_hand` is `(piedras_for - piedras_against) / hands` over the
      published rows, a ratio of sums rather than a mean of per-match ratios;
    * a label with no published hand has `None`, and `None` sorts after every
      measured value, ahead of the vaca difference and then the label.
"""

MIN_LLM_CALLS = 50
MAX_FALLBACK_RATIO = 0.15


def _counter(row, key):
    """One integer counter off a match row. An absent, NULL or non-numeric
    field played no turns of it, so it reads as 0 rather than raising: a dead
    job's row is exactly the row this stage exists to throw away, and making
    the reader crash on it (or skip it silently) is how a dead job's counters
    end up in the table."""
    value = row.get(key)
    if isinstance(value, bool) or value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def is_publishable_match(row):
    if row.get("status") != "done":
        # "degraded" and "error" are the harness's own verdict that this match
        # is not a measurement; a row cannot overrule it with healthy counters.
        return False
    if row.get("vacas_a") is None or row.get("vacas_b") is None:
        # Nothing to compare. There is no win, no loss and no 0-0: a match that
        # never recorded its vacas has no score at all.
        return False
    if _counter(row, "hands") <= 0:
        # No hand was played, so every per-hand number would divide by zero —
        # or, worse, by a default that invents an edge.
        return False
    calls = _counter(row, "llm_turns")
    if calls < MIN_LLM_CALLS:
        return False
    fallbacks = _counter(row, "fallbacks")
    # calls >= MIN_LLM_CALLS > 0, so the denominator is never zero here: the
    # zero-denominator branch a standalone ratio would need is unreachable.
    denominator = calls + fallbacks
    return fallbacks / denominator <= MAX_FALLBACK_RATIO


def _entry(label):
    return {"label": label, "matches": 0, "publishable": 0, "degraded": 0,
            "hands": 0, "piedras_for": 0, "piedras_against": 0,
            "piedras_per_hand": None, "vacas_for": 0, "vacas_against": 0,
            "wins": 0, "losses": 0, "ties": 0}


def _order(entry):
    """The leaderboard's order, as a sort key: measured rows first (the `is
    None` test sorts False before True), then the per-hand edge descending,
    then the vaca difference descending, then the label ascending — so two
    labels that agree on every number still come out in the same order on every
    run, whatever order the rows arrived in."""
    per_hand = entry["piedras_per_hand"]
    return (per_hand is None, -(per_hand or 0.0),
            -(entry["vacas_for"] - entry["vacas_against"]), entry["label"])


def leaderboard(rows):
    table = {}
    for row in rows:
        teams = row.get("teams")
        if not isinstance(teams, (list, tuple)) or len(teams) != 2:
            # No pair of labels means no team to credit; inventing a side would
            # fabricate a row, so the row is skipped like a summary file whose
            # shape the scanner does not recognise.
            continue
        label_a, label_b = teams
        if not isinstance(label_a, str) or not isinstance(label_b, str):
            continue
        publishable = is_publishable_match(row)
        # Read once per row: the same hands and the same two sides are what
        # both labels are built from, and side B's numbers are side A's read
        # from the other end.
        hands = _counter(row, "hands")
        gain_a = _counter(row, "hand_gain_a")
        gain_b = _counter(row, "hand_gain_b")
        vacas_a = _counter(row, "vacas_a")
        vacas_b = _counter(row, "vacas_b")
        sides = ((label_a, True), (label_b, False))
        for label, side_is_a in sides:
            entry = table.setdefault(label, _entry(label))
            entry["matches"] += 1
            if not publishable:
                entry["degraded"] += 1
                continue
            entry["publishable"] += 1
            entry["hands"] += hands
            if side_is_a:
                gain_for, gain_against = gain_a, gain_b
                vacas_for, vacas_against = vacas_a, vacas_b
            else:
                gain_for, gain_against = gain_b, gain_a
                vacas_for, vacas_against = vacas_b, vacas_a
            entry["piedras_for"] += gain_for
            entry["piedras_against"] += gain_against
            entry["vacas_for"] += vacas_for
            entry["vacas_against"] += vacas_against
            if vacas_for > vacas_against:
                entry["wins"] += 1
            elif vacas_for < vacas_against:
                entry["losses"] += 1
            else:
                entry["ties"] += 1
    for entry in table.values():
        entry["piedras_per_hand"] = (
            round((entry["piedras_for"] - entry["piedras_against"])
                  / entry["hands"], 3)
            if entry["hands"] else None)
    return sorted(table.values(), key=_order)
