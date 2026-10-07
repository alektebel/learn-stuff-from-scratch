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
    # TODO: Return True if T2 can see a value that T1 wrote and then aborted.
    raise NotImplementedError("dirty_read")


def non_repeatable_read(level: Isolation) -> bool:
    """T1 reads the same key twice and gets two different committed values."""
    # TODO: Return True if T1 reads the same key twice and gets two different values because T2 committed in between.
    raise NotImplementedError("non_repeatable_read")


def phantom(level: Isolation) -> bool:
    """T1 runs the same range query twice; a row inserted by T2 appears the second time."""
    # TODO: Return True if the same range scan in T1 returns a different number of rows because T2 inserted into the range.
    raise NotImplementedError("phantom")


def lost_update(level: Isolation) -> bool:
    """Both read x, both write x+1, both commit: one increment disappears."""
    # TODO: Return True if both transactions read x, both write x+1, both commit, and x ends up incremented once.
    raise NotImplementedError("lost_update")


def write_skew(level: Isolation) -> bool:
    """Invariant: at least one doctor on call. Each transaction checks the invariant,
    sees two on call, and takes a *different* doctor off call. No key is written twice,
    so no write-write conflict exists, and both commit: nobody is on call."""
    # TODO: Two doctors on call; each transaction checks that both are on call and takes a DIFFERENT one off. Return True if both commit and nobody is left on call. Order the operations carefully.
    raise NotImplementedError("write_skew")


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
