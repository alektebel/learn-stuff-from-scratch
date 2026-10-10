"""
An observed-remove set (OR-set) -- a state-based CRDT for a set with removes.

Sources
-------
  - Shapiro, Preguica, Baquero, Zawirski, "Conflict-free Replicated Data Types",
    SSS 2011 / INRIA RR-7687: the OR-set, where every add carries a unique tag
    and a remove only wipes out the tags it has actually observed.
  - van Steen & Tanenbaum, *Distributed Systems* (3rd ed.), ch. 7, on concurrent
    add/remove and why "last op wins" is not well defined for a set.

Restated in my own words: an add is not a bare element, it is the element paired
with a fresh, globally unique tag. The set keeps, per element, every tag ever
added, plus a tombstone set of tags that have been removed. An element is present
exactly when it has at least one tag that is not tombstoned. `remove(e)` tombstones
only the tags this replica can currently see; a concurrent add elsewhere stamps a
brand-new tag the remover never saw, so it survives. Merging is the union of the
per-element tag sets and the union of the tombstones: unions are commutative,
associative and idempotent. This is the "add wins over concurrent remove" bias.

DESIGN DECISION -- tag the adds, or keep a per-element tombstone?
A per-element "removed" flag is smaller, but it can never be un-set: once the
flag exists, a later re-add is swallowed, and a concurrent add loses to a remove
it never observed. Tags cost memory (one tag per add, kept forever) and buy the
two behaviours this module is built to test: remove-then-add keeps the element,
and a concurrent add survives a remove. That cost -- unbounded tag growth -- is
the known weak point of OR-sets and the reason delta/interval tombstones exist.

DESIGN DECISION -- delete the observed tags on remove, or tombstone them?
Deleting the tags from the add set is tempting and wrong across merges: the other
replica still holds those tags, so the next merge resurrects the element. A
remove must be a monotone fact (a tombstone) so that re-meeting the same add does
not undo it. Cost: `_removed` grows monotonically, like `_adds`.

Run `python3 or_set.py` for the demo measurement (convergence after merges).
"""

import random


class ORSet:
    """An observed-remove set: adds carry unique tags, removes tombstone tags."""

    def __init__(self, node: str) -> None:
        """`node` prefixes this replica's tags; `_clock` makes them unique."""
        self.node = node
        self._clock = 0
        self._adds = {}          # element -> set of tags
        self._removed = set()    # tags that have been observed and removed

    def _tag(self) -> tuple:
        """A tag unique to this replica: (node, next local counter)."""
        self._clock += 1
        return (self.node, self._clock)

    def add(self, element) -> None:
        """Add `element` with a fresh tag that no concurrent remover has seen."""
        self._adds.setdefault(element, set()).add(self._tag())

    def remove(self, element) -> None:
        """Tombstone every tag for `element` this replica has observed."""
        for tag in self._adds.get(element, ()):
            self._removed.add(tag)
        # deliberately keep the tags in _adds: they are the evidence that merge
        # needs in order to know these particular adds were removed.

    def contains(self, element) -> bool:
        """True if some tag for `element` is not tombstoned."""
        return any(tag not in self._removed for tag in self._adds.get(element, ()))

    def elements(self) -> set:
        """The present elements as a plain Python set."""
        return {e for e in self._adds if self.contains(e)}

    def merge(self, other: "ORSet") -> "ORSet":
        """Join: union the tags per element and union the tombstones."""
        out = ORSet(self.node)
        out._clock = max(self._clock, other._clock)
        for e in set(self._adds) | set(other._adds):
            out._adds[e] = set(self._adds.get(e, ())) | set(other._adds.get(e, ()))
        out._removed = set(self._removed) | set(other._removed)
        return out

    def state(self) -> tuple:
        """Canonical view: all (element, tag) pairs and all tombstoned tags."""
        adds = frozenset((e, tag) for e, tags in self._adds.items() for tag in tags)
        return (adds, frozenset(self._removed))


def _demo() -> None:
    """Measure convergence with concurrent adds and removes of the same element."""
    rng = random.Random(13)
    nodes = [f"n{i}" for i in range(4)]
    replicas = [ORSet(n) for n in nodes]

    # Each replica sees a shared element, then some add/remove concurrently.
    for r in replicas:
        r.add("shared")
    seen = replicas[0]
    for r in replicas[1:]:
        seen = seen.merge(r)
    replicas = [r.merge(seen) for r in replicas]   # everyone observes "shared",
                                                   # keeping its OWN node id
    # Deliberately concurrent cluster: half remove, half re-add.
    for i, r in enumerate(replicas):
        if i % 2 == 0:
            r.remove("shared")
        else:
            r.add("shared")
        r.add(f"only-{r.node}")

    merged = replicas[0]
    for r in replicas[1:]:
        merged = merged.merge(r)
    print(f"OR-set after concurrent remove/re-add -> {sorted(merged.elements())}")
    print(f"'shared' survives a concurrent add: {'shared' in merged.elements()}")
    print(f"merge is idempotent: {merged.merge(merged).state() == merged.state()}")


if __name__ == "__main__":
    _demo()
