"""
Anomalies — write the schedule that produces each one
=====================================================

Each function runs one interleaving of two transactions at a given isolation level on a
fresh MVCCStore and returns True if the anomaly was OBSERVED, False if it was prevented
(including by a SerializationFailure aborting one of the transactions).

Run `python3 anomalies.py` to print the matrix your engine produces. The textbook matrix
is in check.py; when yours differs, either the schedule or the engine is wrong, and
working out which is the exercise.
"""

from __future__ import annotations

from mvcc import Isolation, MVCCStore, SerializationFailure


def _try_commit(t) -> bool:
    try:
        t.commit()
        return True
    except SerializationFailure:
        return False


def dirty_read(level: Isolation) -> bool:
    """T2 sees a value T1 wrote but never committed."""
    s = MVCCStore()
    s.load({"x": 10})
    t1, t2 = s.begin(level), s.begin(level)
    t1.write("x", 99)
    seen = t2.read("x")
    t1.abort()
    t2.commit()
    return seen == 99


def non_repeatable_read(level: Isolation) -> bool:
    """T1 reads the same key twice and gets two different committed values."""
    s = MVCCStore()
    s.load({"x": 10})
    t1, t2 = s.begin(level), s.begin(level)
    first = t1.read("x")
    t2.write("x", 20)
    t2.commit()
    second = t1.read("x")
    _try_commit(t1)
    return first != second


def phantom(level: Isolation) -> bool:
    """T1 runs the same range query twice; a row inserted by T2 appears the second time."""
    s = MVCCStore()
    s.load({"emp:1": "ana", "emp:2": "bob"})
    t1, t2 = s.begin(level), s.begin(level)
    before = len(t1.scan("emp:", "emp:~"))
    t2.write("emp:3", "carla")
    t2.commit()
    after = len(t1.scan("emp:", "emp:~"))
    _try_commit(t1)
    return before != after


def lost_update(level: Isolation) -> bool:
    """Both read x, both write x+1, both commit: one increment disappears."""
    s = MVCCStore()
    s.load({"x": 10})
    t1, t2 = s.begin(level), s.begin(level)
    a, b = t1.read("x"), t2.read("x")
    t1.write("x", a + 1)
    t2.write("x", b + 1)
    ok1, ok2 = _try_commit(t1), _try_commit(t2)
    return ok1 and ok2 and s.snapshot()["x"] == 11


def write_skew(level: Isolation) -> bool:
    """Invariant: at least one doctor on call. Each transaction checks the invariant,
    sees two on call, and takes a *different* doctor off call. No key is written twice,
    so no write-write conflict exists, and both commit: nobody is on call."""
    s = MVCCStore()
    s.load({"alice": True, "bob": True})
    t1, t2 = s.begin(level), s.begin(level)
    t1_sees_two = t1.read("alice") and t1.read("bob")  # both check the invariant
    t2_sees_two = t2.read("alice") and t2.read("bob")  # before either acts on it
    if t1_sees_two:
        t1.write("alice", False)
    if t2_sees_two:
        t2.write("bob", False)
    _try_commit(t1)
    _try_commit(t2)
    final = s.snapshot()
    return not final["alice"] and not final["bob"]


ANOMALIES = {
    "dirty read": dirty_read,
    "non-repeatable read": non_repeatable_read,
    "phantom": phantom,
    "lost update": lost_update,
    "write skew": write_skew,
}


def matrix() -> dict[str, dict[Isolation, bool]]:
    return {name: {level: fn(level) for level in Isolation} for name, fn in ANOMALIES.items()}


if __name__ == "__main__":
    m = matrix()
    print(f"{'':22s}" + "".join(f"{l.name[:12]:>14s}" for l in Isolation))
    for name, row in m.items():
        print(f"{name:22s}" + "".join(f"{'OCCURS' if row[l] else '-':>14s}" for l in Isolation))
