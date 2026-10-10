"""Benchmark From Scratch — stage 3 solution: the decision record.

The reasoning lives in `stage_03.py`'s docstring; this file is the code. Two
things to notice: nothing here re-derives a rule the engine already knows (the
phase, the lance, the legal names, the strength and the bet being faced all come
from `mus`), and the record is a flat dict of json-ready scalars, so the log is
one call to `json.dumps` away from being comparable byte for byte.
"""

import json

from mus import team_of

SNAPSHOT_KEYS = ("phase", "lance", "mano", "seat", "team", "legal", "strength",
                 "would_win", "points_a", "points_b", "vacas_a", "vacas_b",
                 "hand_gain_a", "hand_gain_b", "facing_bet", "stake", "previous",
                 "holder_team")


def _probability(value):
    """A confidence is a probability or None, and a bool is neither."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a probability in [0, 1] or None, "
                         "got %r" % (value,))
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be a probability in [0, 1], got %r"
                         % (value,))
    return value


def truth_snapshot(table, seat):
    """What the seat can see, from the table, at this moment."""
    envite = table.envite
    return {
        "phase": table.phase.name,
        "lance": table.lance,
        "mano": table.mano,
        "seat": seat,
        "team": team_of(seat),
        "legal": list(table.legal_actions(seat)),
        "strength": table.strength(seat),
        "would_win": table.would_win(seat),
        "points_a": table.points_a,
        "points_b": table.points_b,
        "vacas_a": table.vacas_a,
        "vacas_b": table.vacas_b,
        "hand_gain_a": table.hand_gain_a,
        "hand_gain_b": table.hand_gain_b,
        "facing_bet": bool(envite["facing"].get(seat)),
        "stake": envite["stake"],
        "previous": envite["previous"],
        "holder_team": envite["holder_team"],
    }


def decision_line(table, seat, decision, *, stats, snapshot, model=None, ok=True,
                  reason=None):
    """One record: what the seat faced, what it chose, and what it cost."""
    if not isinstance(snapshot, dict) or set(snapshot) != set(SNAPSHOT_KEYS):
        raise ValueError("snapshot must be the dict truth_snapshot returned "
                         "BEFORE the action landed, got %r"
                         % (sorted(snapshot) if isinstance(snapshot, dict)
                            else snapshot,))
    if not isinstance(decision, dict):
        raise TypeError("the seat's decision must be a dict, got %r"
                        % (decision,))
    name = decision.get("action")
    if not isinstance(name, str) or not name:
        raise ValueError("the decision must name its action, got %r" % (name,))
    # The action rides along as the engine's own wire dict — payload included,
    # because the payload IS the decision (`cards` on a discard, nothing on a
    # pass) — minus the two fields the harness owns.
    action = {key: value for key, value in decision.items()
              if key not in ("confidence", "fallback")}
    line = dict(snapshot)
    line.update({
        "turn": stats["turns"],
        "hand": table.hand_index,
        "seat": seat,
        "team": snapshot["team"],
        "model": model,
        "phase": snapshot["phase"],
        "lance": snapshot["lance"],
        "action": action,
        "confidence": _probability(decision.get("confidence")),
        "rejections": stats["rejections"],
        "fallback": bool(decision.get("fallback", False)),
        "ok": bool(ok),
        "reason": None if ok else str(reason),
    })
    return line


class DecisionLog:
    """The JSONL sink: one record per line, sorted keys, nothing invented."""

    def __init__(self, sink):
        if not callable(sink):
            raise TypeError("the sink is callable: it is handed each finished "
                            "line, got %r" % (sink,))
        self._sink = sink
        self._lines = 0

    def record(self, line):
        """Serialize one record, hand it to the sink, and return the text."""
        text = json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n"
        self._sink(text)
        self._lines += 1
        return text

    @property
    def lines(self):
        """How many records this log has written."""
        return self._lines
