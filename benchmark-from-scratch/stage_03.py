"""Benchmark From Scratch — stage 3: the decision record.

DESIGN DECISION — why is the truth snapshot taken BEFORE the action?
    Because the state the seat was looking at is the input to its decision, and
    the action destroys it. A snapshot taken afterwards records the position the
    seat CREATED: a seat that calls a bet is recorded as facing a bet it is no
    longer facing, and every metric built on "what was it risking?" — the stake,
    the previous, the fold equity — is then measured on the wrong side of the
    action. One line per decision is only worth writing if the line describes the
    moment the decision was made.

DESIGN DECISION — why is the snapshot a separate function from the line?
    So the caller can take it BEFORE `apply` and pass it in. If the record
    function took the table and the action together, it would have to snapshot
    inside itself — after the action has already landed — and the bug would be
    invisible in every test that only checks field presence.

DESIGN DECISION — why must the JSON keys be sorted, and why no fallback
    `default=str`?
    A benchmark's log is compared, diffed and re-run: two runs of the same seed
    must produce the same bytes, and dict insertion order is an implementation
    detail of whoever built the record. And a value that is not JSON-serialisable
    is a bug in the record, not an object to stringify: `str(card)` written into a
    field the analysis later reads as a name is a corruption that no check
    downstream can see.

DESIGN DECISION — why does a confidence have to be a real probability?
    The calibration probes treat it as one, and they are the one place where a
    `bool` is especially dangerous: `True` is `1` in Python, so a seat that
    answers "did I like the move?" would be measured as a perfectly calibrated
    bettor. A number outside [0, 1] is refused rather than clamped — clamping
    hides the bug (a seat emitting 1.5 has a units problem) and makes every
    published calibration number quietly wrong.

TODO: implement `truth_snapshot`, `decision_line` and `DecisionLog`.
"""

#: The snapshot keys, in the frozen order of the record. Every one is a fact
#: about the position the seat faced, never about the action it chose.
SNAPSHOT_KEYS = ("phase", "lance", "mano", "seat", "team", "legal", "strength",
                 "would_win", "points_a", "points_b", "vacas_a", "vacas_b",
                 "hand_gain_a", "hand_gain_b", "facing_bet", "stake", "previous",
                 "holder_team")


def truth_snapshot(table, seat):
    """What the seat can see, from the table, at this moment.

    The returned dict has exactly `SNAPSHOT_KEYS`:

    - `phase`, `lance` (the lance being played, or None outside the lances),
      `mano`, `seat`, `team`;
    - `legal` — the names the seat may use right now (the engine's own list);
    - `strength` — this seat's hand strength at this lance as a percentile, or
      None; `would_win` — whether this seat's team wins the lance with the cards
      actually held, or None when that is not decided yet;
    - the scoreboard: `points_a`, `points_b`, `vacas_a`, `vacas_b`,
      `hand_gain_a`, `hand_gain_b`;
    - the bet the seat is facing: `facing_bet`, `stake`, `previous`,
      `holder_team`.

    Called BEFORE the action lands: this is the input to the decision, and the
    caller is responsible for taking it at the right moment.
    """
    raise NotImplementedError("stage 3: implement truth_snapshot()")


def decision_line(table, seat, decision, *, stats, snapshot, model=None, ok=True,
                  reason=None):
    """One record: what the seat faced, what it chose, and what it cost.

    `decision` is the seat's own action dict from the frozen shape
    (`{"action": ..., "confidence": ...}` and any payload); `snapshot` is what
    `truth_snapshot` returned before the action was applied; `stats` is the
    match's counter dict.

    The record carries the snapshot keys, plus:

        turn, hand, seat, team, model, phase, lance, action, legal, confidence,
        rejections, fallback, ok, reason

    - `action` is the action as the engine saw it — the wire dict, payload and
      all, because the payload IS the decision (`cards` on a discard is what the
      seat chose to throw away, and a record without it cannot answer what
      happened). The two harness-owned fields, `confidence` and `fallback`, are
      not copied into it; the record's own keys carry them. The name is
      `action["action"]`, which is where every later stage reads it;
    - `confidence` is the seat's declared probability for the move it made: a
      number in [0, 1] or None. A `bool` is not a probability and anything
      outside [0, 1] is a bug — both raise `ValueError`;
    - `rejections` and `fallback` are read from `stats`: how many refusals this
      turn took before it landed, and whether the action recorded is a forced
      legal fallback rather than the seat's own choice;
    - `ok` and `reason` describe the outcome: True with reason None when the
      action landed, False with the engine's words when it was refused.
    """
    raise NotImplementedError("stage 3: implement decision_line()")


class DecisionLog:
    """The JSONL sink: one record per line, sorted keys, and nothing invented.

    `sink` is a callable handed the finished line INCLUDING its newline — a list
    append, a file write, anything. `record(line)` returns the text it wrote.
    """

    def __init__(self, sink):
        raise NotImplementedError("stage 3: implement DecisionLog.__init__()")

    def record(self, line):
        """Serialize one record, hand it to the sink, and return the text."""
        raise NotImplementedError("stage 3: implement DecisionLog.record()")

    @property
    def lines(self):
        """How many records this log has written."""
        raise NotImplementedError("stage 3: implement DecisionLog.lines")
