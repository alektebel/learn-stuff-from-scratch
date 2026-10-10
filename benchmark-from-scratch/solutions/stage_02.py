"""Benchmark From Scratch — stage 2 solution: the match loop.

The reasoning lives in `stage_02.py`'s docstring; this file is the code. The
shape is one function with one loop: deal, snapshot the deal, take turns until
the hand is done, keep the hand's record, deal again. Every rule that the loop
could get wrong — what counts as a turn, what a refused attempt costs, where a
fallback comes from, when to give up — is a line below with a comment saying why.
"""

from mus import TurnLimitExceeded

from stage_01 import gate, new_stats
from stage_03 import decision_line, truth_snapshot

FALLBACK_WARMUP = 10


class DegradedMatch(Exception):
    """The match stopped being about the seats: the turn or fallback rail fired."""

    def __init__(self, rail, note=""):
        super().__init__("%s: %s" % (rail, note))
        self.rail = rail
        self.note = note


def _seat_policies(seats):
    """Four callables, from one callable or a sequence of four."""
    if callable(seats):
        return [seats] * 4
    policies = list(seats)
    if len(policies) != 4 or not all(callable(policy) for policy in policies):
        raise ValueError("seats is one callable or four callables, got %r"
                         % (seats,))
    return policies


def _dealt(table):
    """The four hands AS DEALT: names, so the row is comparable across runs."""
    return [[str(card) for card in table.hands[seat]] for seat in range(4)]


def _record(log, line):
    if log is not None:
        log.record(line)


def _take_turn(table, seat, policy, stats, *, retries, log, model, is_llm):
    """One turn: ask, offer, retry, and fall back to the engine's own default.

    A retry is not a turn (stage 1 counts what landed); a fallback is not the
    model's decision, so it is never counted in `llm_turns`.
    """
    snapshot = None
    for _ in range(retries + 1):
        snapshot = truth_snapshot(table, seat)
        stats["calls"] += 1
        decision = policy(table, seat, list(table.legal_actions(seat)))
        outcome = gate(table, seat, decision, stats=stats)
        if outcome["ok"]:
            if is_llm:
                stats["llm_turns"] += 1
            _record(log, decision_line(table, seat, decision, stats=stats,
                                       snapshot=snapshot, model=model, ok=True,
                                       reason=None))
            return
    # The seat could not produce a legal action. The engine's own default is the
    # only fallback that is guaranteed legal, payload included.
    fallback = table.default_action(seat)
    if fallback is None:
        raise DegradedMatch("fallbacks", "no legal action for seat %d in %s"
                            % (seat, table.phase.name))
    stats["calls"] += 1
    outcome = gate(table, seat, fallback, stats=stats)
    if not outcome["ok"]:
        raise DegradedMatch("fallbacks", "the engine refused its own default: %s"
                            % (outcome["reason"],))
    stats["fallbacks"] += 1
    _record(log, decision_line(table, seat, dict(fallback, fallback=True),
                               stats=stats, snapshot=snapshot, model=model,
                               ok=True, reason=None))


def run_match(table, seats, *, names, llm=None, hands, turn_limit=200, retries=4,
              on_hand=None, log=None):
    """Play `hands` hands at `table` and return the match's row."""
    names = list(names)
    if len(names) != 4:
        raise ValueError("names are the four seat labels, got %r" % (names,))
    policies = _seat_policies(seats)
    llm_flags = [False] * 4 if llm is None else [bool(flag) for flag in llm]
    if len(llm_flags) != 4:
        raise ValueError("llm marks the four seats, got %r" % (llm,))
    if isinstance(hands, bool) or not isinstance(hands, int) or hands < 1:
        raise ValueError("hands is how many hands to play, got %r" % (hands,))

    stats = new_stats()
    teams = [names[0], names[1]]
    row = {"matchup": "%s-vs-%s" % (teams[0], teams[1]), "seed": table.seed,
           "teams": teams, "names": names, "llm": llm_flags, "status": "done",
           "hands": 0, "turns": 0, "llm_turns": 0, "fallbacks": 0,
           "rejections": 0, "vacas_a": 0, "vacas_b": 0, "hand_wins_a": 0,
           "hand_wins_b": 0, "hand_gain_a": 0, "hand_gain_b": 0, "deals": [],
           "note": None}
    records = []
    try:
        for _ in range(hands):
            table.deal()
            dealt = _dealt(table)
            row["deals"].append(dealt)
            turns_at_start = stats["turns"]
            while table.phase.name != "DONE":
                played = stats["turns"] - turns_at_start
                if played >= turn_limit:
                    raise DegradedMatch("turn_limit",
                                        "hand took more than %d actions"
                                        % (turn_limit,))
                if stats["fallbacks"] > FALLBACK_WARMUP:
                    raise DegradedMatch("fallbacks",
                                        "more than %d fallbacks in the match"
                                        % (FALLBACK_WARMUP,))
                seat = table.current_seat
                _take_turn(table, seat, policies[seat], stats,
                           retries=retries, log=log, model=names[seat],
                           is_llm=llm_flags[seat])
            record = {"kind": "hand", "hand": table.hand_index,
                      "hand_gain_a": table.hand_gain_a,
                      "hand_gain_b": table.hand_gain_b,
                      "hand_winner": table.hand_winner,
                      "vacas_a": table.vacas_a, "vacas_b": table.vacas_b,
                      "dealt": dealt}
            records.append(record)
            if on_hand is not None:
                on_hand(record)
            row["hands"] += 1
    except DegradedMatch as exc:
        # The row says what happened and why, and carries what the match managed.
        row["status"] = "degraded"
        row["note"] = str(exc)
    except TurnLimitExceeded as exc:
        row["status"] = "degraded"
        row["note"] = "engine turn limit: %s" % (exc,)
    except Exception as exc:  # our bug: labelled, never filed as a result
        row["status"] = "error"
        row["note"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        row["turns"] = stats["turns"]
        row["llm_turns"] = stats["llm_turns"]
        row["fallbacks"] = stats["fallbacks"]
        row["rejections"] = stats["rejections"]
        row["vacas_a"], row["vacas_b"] = table.vacas_a, table.vacas_b
        for record in records:
            row["hand_gain_a"] += record["hand_gain_a"]
            row["hand_gain_b"] += record["hand_gain_b"]
            if record["hand_winner"] == 0:
                row["hand_wins_a"] += 1
            elif record["hand_winner"] == 1:
                row["hand_wins_b"] += 1
    return row
