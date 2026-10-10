"""
replica.py -- one replica's write-ahead log.

Source: Kleppmann, *Designing Data-Intensive Applications*, chapter 5
("Replication"), the section on leader-based replication. DDIA describes the
simplest scheme: the leader appends every write to its log and ships the log, in
order, to each follower; a follower applies the writes in the same order and so
ends up in the same state. It also names the failure that follows -- a follower
can fall behind, and it must be able to catch up from the leader rather than
guess.

Restated in my own words: the unit of replication is a positional log. Write
number `i` has a unique slot `i`; a replica that already holds slot `i` will not
accept a different write there. This is the property that stops a lagging or
partitioned replica from silently growing a *forked* history.

DESIGN DECISION -- a list of log entries, or a key -> value map?
    A map (last-write-wins per key) is less code but loses the ordering that
    quorum replication needs: "has this replica seen the write with version v?"
    becomes a question about a key's history it no longer keeps. Chosen: a
    positional log; `applied` is a derived view.
    Cost: truncating a log entry means rebuilding `applied`, which is O(log).

DESIGN DECISION -- what does `append` do with a non-contiguous index?
    Accept it into a dict (out-of-order buffer) or refuse it. Chosen: refuse.
    A follower only advances one entry at a time; a gap means it missed an
    earlier write, and accepting the later one would leave a hole that a later
    read could expose. Refusing forces the caller (the leader) to run catch-up.
    Cost: the leader must resend the missing prefix, not just the newest entry.

DESIGN DECISION -- how is "newest value for a key" decided?
    By log position or by the entry's `version`. Chosen: the highest version.
    In this module `version == index`, so the two agree, but reading the version
    says the intent out loud and is the hook a real system uses when versions
    come from a clock rather than a counter. Cost: `applied` stores a tuple and
    every write replaces it.
"""

from typing import Any, Dict, List, Optional, Tuple

__all__ = ["Replica"]


class Replica:
    """A single node's log plus the key/value view derived from it."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.log: List[dict] = []          # positional: log[i] is the entry with index i
        self.applied: Dict[str, Tuple[int, Any]] = {}   # key -> (version, value)
        self.paused = False                # a slow follower: receives nothing while paused
        self.crashed = False               # a stopped node: receives nothing at all
        self.received = 0                  # messages actually processed

    # -- the log ------------------------------------------------------------

    def append(self, entry: dict) -> bool:
        """Append `entry` iff its index is exactly the next slot. Return success."""
        index = entry["index"]
        if index != len(self.log):
            return False
        self.log.append(dict(entry))
        self.applied[entry["key"]] = (entry["version"], entry["value"])
        return True

    def truncate(self, index: int) -> None:
        """Drop every entry at or after `index` and rebuild the derived view."""
        if index < 0:
            return
        del self.log[index:]
        self.applied = {}
        for entry in self.log:
            self.applied[entry["key"]] = (entry["version"], entry["value"])

    def get(self, index: int) -> Optional[dict]:
        """The entry at `index`, or None if this replica has not reached it."""
        if 0 <= index < len(self.log):
            return self.log[index]
        return None

    def value(self, key: str) -> Optional[Tuple[int, Any]]:
        """The newest `(version, value)` this replica holds for `key`, or None."""
        return self.applied.get(key)

    # -- the wire -----------------------------------------------------------

    def receive(self, src: str, msg: dict) -> None:
        """Handle one message. A paused or crashed replica stays silent."""
        if self.paused or self.crashed:
            return
        self.received += 1
        kind = msg["kind"]
        if kind == "append":
            self.append(msg["entry"])
        elif kind == "truncate":
            self.truncate(msg["index"])


def _demo() -> None:
    """Show contiguous appends, a refused gap, latest-version reads and rollback."""
    r = Replica("A")
    r.append({"index": 0, "key": "x", "value": "one", "version": 0})
    r.append({"index": 1, "key": "x", "value": "two", "version": 1})
    print("log length:", len(r.log), " value(x):", r.value("x"))
    accepted = r.append({"index": 3, "key": "x", "value": "gap", "version": 3})
    print("append at a gap accepted?", accepted, " log length:", len(r.log))
    r.truncate(1)
    print("after truncate(1): length", len(r.log), " value(x):", r.value("x"))


if __name__ == "__main__":
    _demo()
