"""Two's-complement integers of any width.

The material is CS:APP (Bryant & O'Hallaron), chapter 2, "Representing and Manipulating
Information", section 2.2 (integer representations) and 2.3 (integer arithmetic). The
chapter's central claim is that a machine integer is a *bit pattern* plus a *decoding*:
the same 32 bits are 4294967295 unsigned and -1 signed. This file makes that split
explicit, for any width, so the decoder is an arithmetic formula rather than a type.

DESIGN DECISION - fixed-width decoding, or Python's unbounded ints?
Python ints never overflow, so the language hides exactly the phenomenon this chapter is
about. **Chosen: keep the learner's values as ordinary Python ints, but make every
operation take an explicit `width`** and reduce modulo 2**width. The cost is that a value
can still be out of range on input; the benefit is that the machine's truncation and its
sign decoding are written down, not inherited from the interpreter.

DESIGN DECISION - one add that wraps, or one that checks?
A single `add` cannot both wrap silently and raise: they are opposite contracts. The
chapter says signed overflow is *undefined* in C and *flag* in the CPU, and Python simply
does not overflow. **Chosen: two functions named for their contract** - `add_wrap`
reduces modulo 2**width and never raises, `add_checked` raises `OverflowError` when the
mathematical sum leaves the signed range. A limit case is the caller that picked the
wrong one.

    python3 twos_complement.py      # prints the measurements this file promises
"""


def _signed_range(width: int) -> tuple[int, int]:
    """The inclusive signed range [-2**(width-1), 2**(width-1) - 1] for `width` bits."""
    return -(1 << (width - 1)), (1 << (width - 1)) - 1


def _require_width(width: int) -> None:
    """Reject a width that is not a positive whole number of bits."""
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise ValueError(f"width must be a positive integer number of bits, got {width!r}")


def to_bits(value: int, width: int) -> int:
    """Encode a signed value as its `width`-bit two's-complement pattern (unsigned int).

    The pattern is `value` reduced modulo 2**width, i.e. `value & (2**width - 1)`.
    Overflow therefore *wraps* rather than raising: this is the machine's behaviour,
    not Python's. The result always satisfies 0 <= result < 2**width.
    """
    _require_width(width)
    return value & ((1 << width) - 1)


def from_bits(bits: int, width: int) -> int:
    """Decode a `width`-bit unsigned pattern as a signed two's-complement integer.

    If the most significant bit (the sign bit) is set, subtract 2**width; otherwise the
    value is the pattern itself. `bits` must already be a valid pattern in [0, 2**width),
    so a caller that forgot to mask is told, instead of being silently wrapped.
    """
    _require_width(width)
    if not isinstance(bits, int) or isinstance(bits, bool) or not 0 <= bits < (1 << width):
        raise ValueError(f"{bits!r} is not a {width}-bit pattern (0 <= bits < 2**{width})")
    sign_bit = 1 << (width - 1)
    if bits & sign_bit:
        return bits - (1 << width)
    return bits


def add_wrap(a: int, b: int, width: int) -> int:
    """Add two signed `width`-bit integers; signed overflow wraps modulo 2**width.

    This is the arithmetic a CPU actually performs: the carry out of the top bit is
    discarded, and the result is re-decoded as signed. It never raises for a magnitude
    reason (only for a bad width), which is why the chapter calls C's signed overflow
    *undefined* while this function calls it *defined, and wrong if you did not mean it*.
    """
    _require_width(width)
    mod = 1 << width
    return from_bits((to_bits(a, width) + to_bits(b, width)) % mod, width)


def add_checked(a: int, b: int, width: int) -> int:
    """Add two signed `width`-bit integers, raising `OverflowError` on overflow.

    The mathematical sum is compared against the signed range before it is trusted, so a
    caller that cannot tolerate wraparound gets a failure at the exact operation that
    overflowed instead of a plausible wrong answer much later.
    """
    _require_width(width)
    lo, hi = _signed_range(width)
    total = a + b
    if not lo <= total <= hi:
        raise OverflowError(
            f"{a} + {b} does not fit in signed {width}-bit (range {lo}..{hi}); "
            "use add_wrap for wrapping arithmetic")
    return total


if __name__ == "__main__":
    print("i32 two's complement: -1 -> "
          f"0x{to_bits(-1, 32):08X}, decoded back -> {from_bits(to_bits(-1, 32), 32)}")
    top = (1 << 31) - 1
    wrapped = add_wrap(top, 1, 32)
    print(f"i32 wrapping add: 0x{top:08X} + 1 -> {wrapped} (0x{to_bits(wrapped, 32):08X})")
    try:
        add_checked(top, 1, 32)
        print("guarded add: DID NOT RAISE (bug)")
    except OverflowError as exc:
        print(f"guarded add raised: {exc}")
    print(f"i8 decode: 0xFF -> {from_bits(0xFF, 8)}, 0x80 -> {from_bits(0x80, 8)}")
