"""Benchmark From Scratch — stage 10: the mirrored pair.

DESIGN DECISION — why is every match played TWICE, in both seat orientations?
    The four seats are not symmetric. The mano discards first and speaks first in
    the lances; the a-side of the deal is a different set of cards with a
    different distance to the vaca. And the decisions a seat makes are
    seat-dependent: a pass can be right for the hand and wrong for the seat. So a
    single match between two models measures skill PLUS a per-seat advantage, with
    no way to tell them apart. Playing the same matchup under the same seed with
    the models swapped makes the seat advantage a constant that appears in both
    matches with opposite signs — and a constant with opposite signs cancels when
    the two are added.

DESIGN DECISION — why is a match keyed by the matchup AND the seed, and why must
    the card stream depend on the seed alone?
    Because the pair only cancels what is common to both halves. If the deal is
    drawn from the play's own random stream, then the two orientations play
    DIFFERENT cards, and the difference between them is dealt rather than played:
    the resulting number is noise wearing the word "skill". The deal for a seed
    must be reproducible from the seed alone — fork it from the match's own
    generator before a single decision is made, and assert it in a check.

DESIGN DECISION — why is a half pair dropped instead of published alone?
    A single orientation is exactly the biased quantity the stage exists to
    cancel, and it is the quantity that looks like the most precise measurement in
    the whole table: one number, one matchup, no averaging. Publishing it invites
    the comparison it cannot support. A pair that is missing a half, or whose half
    was degraded, has no seat-balanced number and must disappear — not fall back
    to "the one we have".

DESIGN DECISION — why sum the two orientations, and divide by BOTH matches'
    hands?
    The two diffs share the same true skill and carry the seat advantage with
    opposite signs, so the sum is twice the skill — the signal doubles while the
    variance of each half is unchanged, which is the cheapest variance reduction
    available in this whole benchmark. `hands` is the number of hands PLAYED to
    produce those diffs, i.e. the sum over both matches; dividing by one match's
    hands would double every per-hand number in the report.

TODO: implement `build_jobs` and `paired_rows`.
"""


def build_jobs(pairings, seeds, *, mirror=True):
    """The schedule: one job per (model_a, model_b, seed).

    `pairings` are UNORDERED pairs of model labels; `seeds` are the seeds to play
    under. Returns a list of `(model_a, model_b, seed)` in seed-major order (every
    pairing under the first seed, then the second, ...).

    - `mirror=True` (the default): every pairing is played under every seed in
      BOTH orientations, so the two halves of a pair are the same cards.
    - `mirror=False`: one orientation only. The run still looks complete — every
      matchup, every seed — and every paired comparison silently disappears,
      because the two halves now sit on different cards.
    """
    raise NotImplementedError("stage 10: implement build_jobs()")


def paired_rows(entries):
    """The paired comparison: one entry per matchup per seed.

    `entries` are match rows in the frozen shape (`teams`, `seed`, `status`,
    `hands`, `hand_gain_a`, `hand_gain_b`). A `status` other than `"done"` is a
    degraded match and is not a measurement.

    Returns one dict per (sorted matchup, seed) that has BOTH orientations::

        {
          "models": [m0, m1],            # sorted labels; the diff is m0's view
          "seed": int,
          "seat_a": row, "seat_b": row,  # the two halves, m0 first in seat_a
          "piedra_diff_seat_a": float,   # m0's piedra difference with m0 in a
          "piedra_diff_seat_b": float,   # and with m0 in b
          "paired_diff": float,          # their sum: the seat bias cancels
          "hands": int,                  # hands played in BOTH halves
          "per_hand": float | None,      # paired_diff / hands, 3 decimals
        }

    A matchup/seed with only one orientation, or with a degraded half, produces no
    entry at all; the same orientation twice is a broken schedule and raises
    `ValueError`.
    """
    raise NotImplementedError("stage 10: implement paired_rows()")
