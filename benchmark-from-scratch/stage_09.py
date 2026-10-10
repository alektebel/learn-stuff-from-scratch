"""Benchmark From Scratch (Mus) — stage 9: which rows may be published, and the
leaderboard built from them.

Stage 2 produced a row per match, and some of those rows are worthless: a
rate-limit cascade finishes `"done"` with almost no real model play, a match
aborted mid-hand has no vacas, a crashed job has no hands at all. A leaderboard
that averages them in is measuring the weather in the API, not the models. So
this stage answers two questions and nothing else — MAY this row be published,
and what does the table look like once the rows that may not are gone.

DESIGN DECISION — the fallback rate is read over the MODEL'S OWN decisions plus
    the fallbacks they forced, not over the match's turns.
    A tournament row is four seats, and only some of them are models: the
    baseline seats keep playing while a model is rate-limited and waits.
    `fallbacks / turns` therefore divides the model's failures by everyone's
    play — a degraded model with 8 fallbacks in 20 decisions reads as 8/300 =
    2.7% in a 300-turn match, under any ceiling, and the row enters the table.
    The denominator has to be the decisions the model actually made
    (`llm_turns`) plus the turns the fallback machinery made FOR it
    (`fallbacks`, 0 or 1 per fallback), because that pair and only that pair
    describes the session the numbers came out of. It is called a ratio, not a
    fraction of the match, on purpose: it answers "how often did this model
    play by itself" and nothing else.
    The zero-denominator case (`llm_turns + fallbacks == 0`) needs no branch:
    the call floor below already rejects any row under 50 model decisions, so a
    row with no decisions never reaches the division.

DESIGN DECISION — the gate is a function of the ROW, and a rejected row is
    counted rather than dropped.
    `is_publishable_match(row)` is pure and reads the row it is given: `status
    == "done"`, both vacas present, `hands > 0`, at least `MIN_LLM_CALLS` model
    decisions, and a fallback ratio at or under `MAX_FALLBACK_RATIO`. Every one
    of those is a way the row is not evidence, and each has a different cause —
    a cascade, an abort, a crash — so the leaderboard cannot just filter and
    forget: it reports `publishable` and `degraded` per label, because "this
    label has no data" and "this label's data is all noise" are different
    findings and a table that merges them hides which one happened.
    The gate is checked ONCE, here, and the leaderboard never re-derives it:
    two implementations of publishability is two answers to the same question,
    and the stage-2 row already carries `status` and the counters.

DESIGN DECISION — a row credits BOTH of its labels, with the sides' numbers
    swapped.
    A match is not one team's result: `row["teams"]` is `[label_a, label_b]`,
    and the same vacas that are a win for `label_a` are a loss for `label_b`.
    So the row is added twice — to `label_a` with `hand_gain_a`/`vacas_a` on
    the FOR side and `hand_gain_b`/`vacas_b` on the AGAINST side, and to
    `label_b` with the two sides swapped. Crediting only the first label (or
    both labels with side A's numbers) makes every second team's row read as a
    win and halves the table; a label that never played is absent from the
    leaderboard rather than sitting in it with zeros.
    A row with no pair of string labels cannot be credited to a team at all
    (there is no side to invent) and is skipped, the way the reference scanner
    skips files whose shape it does not recognise.

DESIGN DECISION — `piedras_per_hand` is the ratio of the SUMS, not the mean of
    the per-match ratios.
    The leaderboard measures an edge per hand of play. Summing the piedras of
    every published hand and dividing by the hands summed over the same rows
    gives that, and a two-hand match with a +5 edge cannot outvote a forty-hand
    match with a +1 edge. Averaging each match's ratio and then the ratios
    weights a short match exactly as much as a long one — a 1-hand fluke counts
    as much as a session — and it is what you get by reaching for `sum(...)/
    len(...)` over rows instead of over hands. The denominator is the hands of
    the PUBLISHED rows only: a degraded row's hands went into a session nobody
    may rank, and putting them under the divider is how its discarded piedras
    sneak back into the number.

DESIGN DECISION — a label with nothing to show sorts LAST, and the whole order
    is decided by the row.
    `piedras_per_hand` is `None` when no published hand exists; `None` is not
    zero. Zero says "measured, and the edge is nil"; `None` says "not measured".
    Sorting a `None` as `0.0` puts a label nobody has data for above every label
    that is actually losing — the one thing a leaderboard must never do, because
    the reader takes the top row as the winner. So: measured rows first,
    descending by the per-hand edge; then the vaca difference (the same number
    from the perspective of a coarser scoreboard); then the label, ascending, so
    two labels that agree on everything still get a stable, reproducible order
    instead of whatever order the rows happened to arrive in.

TODO: implement `is_publishable_match` and `leaderboard`.

    MIN_LLM_CALLS = 50
    MAX_FALLBACK_RATIO = 0.15
        The shipped thresholds. A match that finished with fewer than 50 model
        decisions, or that fell back on more than 15% of its decisions, is a
        measurement of the harness, not of the model. Both are constants of the
        course, since every run is compared under the same gate.

    def is_publishable_match(row) -> bool
        True when a match row is evidence: `status == "done"`, `vacas_a` and
        `vacas_b` both not None, `hands > 0`, `llm_turns >= MIN_LLM_CALLS`, and
        `fallbacks / (llm_turns + fallbacks) <= MAX_FALLBACK_RATIO`. Missing
        counters read as 0. Pure: it reads the row and changes nothing.

    def leaderboard(rows) -> list[dict]
        One entry per label that appears in `rows[*]["teams"]`, ordered by
        `piedras_per_hand` descending with the data-less labels last, the vaca
        difference as the tiebreak and the label as the last resort. Each entry:

            {"label", "matches", "publishable", "degraded", "hands",
             "piedras_for", "piedras_against", "piedras_per_hand",
             "vacas_for", "vacas_against", "wins", "losses", "ties"}

        `matches`/`publishable`/`degraded` count rows (`degraded` is the rows
        the gate rejected); every other number is summed over the PUBLISHED
        rows only, and `piedras_per_hand` is `(piedras_for - piedras_against) /
        hands` rounded to 3 decimals, or `None` when `hands` is 0. `wins`,
        `losses` and `ties` are the vaca comparison of each published row from
        that label's side.
"""

MIN_LLM_CALLS = 50
MAX_FALLBACK_RATIO = 0.15


def is_publishable_match(row):
    raise NotImplementedError("stage 9: implement is_publishable_match()")


def leaderboard(rows):
    raise NotImplementedError("stage 9: implement leaderboard()")
