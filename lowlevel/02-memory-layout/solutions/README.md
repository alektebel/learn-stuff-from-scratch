# Memory Layout — Solutions

Complete versions of the templates in the parent directory. Pure Python 3,
standard library only. Run them from inside this directory (they import each
other by name):

```bash
cd solutions
python3 layout.py    # sizes, alignments, padding, packed vs natural, format strings
python3 reorder.py   # before/after sizes for four declarations
```

## Expected output — `python3 layout.py`

```
fields                                       sizeof align  pad packed unaligned (packed)
c:char, i:int, d:char                            12     4    6      6 i
i:int, c:char                                     8     4    3      5 -
a:short, in:struct, b:char                       16     4    5     11 in
c:char, w:longdouble, d:char                     48    16   30     18 w

format string packed : <bid calcsize 13
format string natural: <bxxxid calcsize 16
packed bytes         : 41070000000000000000000440
```

Reading it:

- `pad` is `sizeof - sum(field sizes)`: `{char; int; char}` spends 6 of its 12
  bytes on holes (3 internal + 3 trailing).
- The nested `in:struct` is one 8-byte member aligned to 4, and the outer struct
  is 16 — its own padding comes from the nested alignment propagating.
- `longdouble` (16 bytes, aligned to 16) is the over-aligned case: 30 padding
  bytes, and `sizeof` 48 because the *whole* struct rounds to 16.
- The `unaligned (packed)` column lists the members the packed layout leaves
  misaligned; the natural layout of the second row reports none.

## Expected output — `python3 reorder.py`

```
declaration                        before after saved  reordered
['c', 'i', 'd']                        12     8     4  i, c, d
['a', 'b', 'c']                        24    16     8  b, c, a
['p', 'i', 'x']                        16    16     0  p, i, x
['i', 'j']                              8     8     0  i, j
```

`{char; int; char}` shrinks 12 → 8 (the `int` first, the two `char`s after the
last round-up is the only remaining size). `{pointer; int; char}` is already
minimal, so `saved` is 0 — reordering never *grows* a struct either.
