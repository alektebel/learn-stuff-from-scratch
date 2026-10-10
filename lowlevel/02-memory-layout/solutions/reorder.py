"""
Reordering struct fields to shrink a struct.

Source: Bryant & O'Hallaron, *Computer Systems: A Programmer's Perspective*
(CS:APP), Chapter 3 "Machine-Level Representation of Programs", section 3.9
"Heterogeneous Data Structures", the data-alignment discussion (3.9.3). The book's
worked example rearranges a struct's fields so the padding disappears. Restated:

  - Padding appears whenever a small member sits before a larger one (a `char`
    before an `int` leaves 3 holes) and, once, at the end (to round the struct up
    to its alignment).
  - If you declare the members from the largest alignment down, each member
    already starts on a boundary, so there is nothing to pad between them; the
    total shrinks to the sum of the field sizes rounded up to the struct's
    alignment.
  - Sorting by descending alignment is not just a heuristic here: when every
    type's size is a multiple of its alignment (true for the LP64 types), no
    permutation can do better, and this module's checks prove it by brute force
    on small structs.

The cost is real and worth naming: reordering changes the *declaration order*,
which changes the byte string that goes to a file or the network, and it cannot
be done to a type whose layout is part of an ABI (a struct shared with C or
written to disk must keep its order). Reordering is a compile-time choice, not a
runtime transformation.

DESIGN DECISION -- what counts as the goal?
    Minimum total size, not "no padding": a struct of three chars has no padding
    and no order is better. **Chosen:** `minimal_order` returns a field order
    whose size equals the brute-force minimum; `padding_bytes` reports the holes
    so a shrinking is only claimed when there is something to reclaim.
"""

from layout import Struct, _describe, align_up


def padding_bytes(fields, packed: bool = False) -> int:
    """Bytes in the struct that belong to no member (internal + trailing)."""
    s = Struct(fields, packed)
    payload = sum(_describe(spec)[0] for _, spec in fields)
    return s.size - payload


def minimal_order(fields) -> list:
    """
    A permutation of `fields` with the smallest natural-alignment size.

    Largest alignment first; ties broken by size then by the original order
    (the sort is stable), so the result is deterministic.
    """
    return sorted(fields, key=lambda f: (-_describe(f[1])[1], -_describe(f[1])[0]))


def shrink_struct(fields, packed: bool = False) -> Struct:
    """A Struct holding the reordered fields (packed mode has nothing to reclaim)."""
    if packed:
        return Struct(list(fields), packed=True)
    return Struct(minimal_order(fields))


def bytes_saved(fields) -> int:
    """How many bytes `minimal_order` reclaims for this declaration."""
    return Struct(fields).size - Struct(minimal_order(fields)).size


if __name__ == "__main__":
    examples = [
        [("c", "char"), ("i", "int"), ("d", "char")],
        [("a", "char"), ("b", "double"), ("c", "int")],
        [("p", "pointer"), ("i", "int"), ("x", "char")],
        [("i", "int"), ("j", "int")],
    ]
    print(f"{'declaration':<34} {'before':>6} {'after':>5} {'saved':>5}  reordered")
    for fields in examples:
        before = Struct(fields)
        after = shrink_struct(fields)
        order = ", ".join(n for n, _ in after.fields)
        print(f"{str([n for n, _ in fields]):<34} {before.size:>6} {after.size:>5} "
              f"{bytes_saved(fields):>5}  {order}")
