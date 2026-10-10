# Bits: integers, floats, endianness

How a machine turns numbers into bytes and back — two's-complement integers of any width,
IEEE-754 binary32/binary64, and byte order — in pure Python (standard library only), built
one mechanism at a time.

It is the first node of the skill tree's `lowlevel` track: the material of
*Computer Systems: A Programmer's Perspective* (Bryant & O'Hallaron), chapter 2,
"Representing and Manipulating Information". Every later node that reads a struct out of
memory, writes a file format, or debugs a byte order stands on this one.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Two's complement | encode/decode a signed value at any width, wrapping | `twos_complement.py` | 1-2 |
| Signed overflow | one add that wraps, one guarded add that raises | `twos_complement.py` | 3 |
| IEEE-754 fields | binary32/binary64 to and from their bit patterns with `struct` | `float754.py` | 4 |
| Special values | `-0.0`, `±inf`, quiet/signaling NaN, payload | `float754.py` | 5 |
| Subnormals | exponent 0 with a nonzero fraction is a real number | `float754.py` | 6 |
| Byte order | little/big endian, a measured host detector, byte swap | `endianness.py` | 7 |
| Hex dump | known patterns, `0xFFFFFFFF = -1` in i32 | `endianness.py` | 8 |

## How to use this directory

The three top-level `.py` files are **templates**: each function you write keeps its
signature and docstring, has a `TODO` with a hint, and raises `NotImplementedError`.
`solutions/` holds working versions for when you are stuck, or to compare afterwards.

```bash
cd lowlevel/01-bit-representation
python3 check.py        # what to build next; stops at the first gap
python3 check.py 3      # one step
python3 check.py 4 6    # a range
python3 check.py --all  # everything
```

`check.py` runs 8 checks against **your** code and never imports `solutions/`. The
references are the standard library itself — `int.to_bytes(..., signed=True)` and
`struct.pack/unpack` — plus hand-computed bit patterns for the cases where the learner and
the reference could share a mistake.

**The checker was itself tested.** Five classic bugs were planted in copies of the
solutions, and each one has to be caught by its check:

| Planted bug | Caught by |
|---|---|
| the sign bit off by one in decode | step 1 |
| a "guarded" add that wraps silently | step 3 |
| float bits read in the wrong byte order | step 4 |
| a denormal flushed to zero | step 6 |
| little-endian bytes read as big-endian | step 7 |

## Design decisions, named

Each file opens with its decisions and what they cost. In short:

- **Fixed-width decoding, on top of Python's unbounded ints** (`twos_complement.py`). The
  language hides overflow; every operation takes an explicit `width` and reduces modulo
  `2**width`, so the machine's truncation is written down rather than inherited.
- **Two adds with opposite contracts** (`add_wrap`, `add_checked`). One cannot both wrap
  and raise. `add_wrap` is the CPU; `add_checked` is the caller who meant it. Step 3 is the
  limit case for picking the wrong one.
- **`struct` moves the bytes, the fields are decoded by hand** (`float754.py`). Re-deriving
  the value loses the NaN payload and the sign of zero; keeping the bytes and inspecting
  the fields keeps both checkable.
- **Compare bit patterns, not floats** (`float754.py`). `==` cannot see `-0.0` and is never
  true for NaN; the round-trip is compared as bits.
- **Measure the byte order, do not ask** (`endianness.py`). `sys.byteorder` is the
  interpreter's claim; packing 1 in native order and reading its first byte is a
  measurement with a falsifiable contract.
- **A hand-written hex dump** (`endianness.py`). `bytes.hex(' ')` would do; writing the
  two-digit loop is how you notice a byte is two hex digits.

## Questions to answer before reading the solutions

1. `0xFFFFFFFF` is 4294967295 unsigned and -1 signed. Where in your code does that
   ambiguity live, and why is it not a `bool` flag on the value?
2. C calls signed overflow *undefined behaviour*; `add_wrap` calls it *defined, and wrong
   if you did not mean it*; `add_checked` calls it a *failure*. Which contract does a real
   CPU provide, and which one does a real language?
3. Step 5 requires a **signaling** NaN to survive, not just "a NaN". Which bit of the
   fraction decides that, and what does it mean that Python's `==` can never tell them
   apart?
4. A denormal has no implicit leading 1. Step 6 shows the smallest one is `2**-149` for
   binary32. Reconstruct that exponent from the field layout without looking at the code.
5. On a big-endian machine, would step 7 still pass unchanged? What would you have to edit
   in `endianness.py` if the test were run there, and what does the fact that the *checker*
   would not change tell you?

## Limits

- Standard library only: integers use Python's arbitrary-precision ints as the storage
  type, so the "word" is a number with an explicit width, not a real fixed-width register.
- binary32/binary64 only. `binary16`, x87 80-bit, bfloat16 and decimal floating point are
  deliberately left out; the field layout would generalise, the payload rules would not.
- The host detector reports the *interpreter's* native order, which for a normal build is
  the machine's; it says nothing about a file's order, which is exactly why the explicit
  `to_*`/`from_*` functions exist.
- No bitfields or packed structs; the offsets and padding of chapter 3 are the subject of
  `lowlevel-02-memory-layout`.
